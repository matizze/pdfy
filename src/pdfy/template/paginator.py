"""Page lifecycle, safe pagination and machine-readable layout traces."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from xml.sax.saxutils import escape

from reportlab.platypus import Paragraph

from pdfy.design.dimensions import (
    BOTTOM_SAFE,
    CONTENT_WIDTH,
    MARGIN,
    PAGE_HEIGHT,
    PAGE_WIDTH,
)


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y + self.height


@dataclass(frozen=True)
class TraceItem:
    kind: str
    bbox: BoundingBox
    zone: str = "content"
    component_type: str | None = None
    label: str | None = None


@dataclass
class PageTrace:
    number: int
    role: str
    section_index: int | None = None
    section_title: str | None = None
    safe_area: BoundingBox = field(
        default_factory=lambda: BoundingBox(
            MARGIN, BOTTOM_SAFE, CONTENT_WIDTH, PAGE_HEIGHT - BOTTOM_SAFE - MARGIN,
        )
    )
    items: list[TraceItem] = field(default_factory=list)


@dataclass
class LayoutTrace:
    pages: list[PageTrace] = field(default_factory=list)

    @property
    def section_start_pages(self) -> dict[int, int]:
        return {
            page.section_index: page.number
            for page in self.pages
            if page.role == "section" and page.section_index is not None
        }

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["section_start_pages"] = self.section_start_pages
        return data


def plain_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return (
        text.strip()
        .replace("–", "-")
        .replace("—", "-")
        .replace("‑", "-")
        .replace("\u00a0", " ")
    )


def safe_text(value: Any) -> str:
    return escape(plain_text(value)).replace("\n", "<br/>")


class RenderContext:
    """State shared by component renderers.

    Coordinates use the native PDF convention: origin at the bottom left.
    """

    def __init__(self, canvas, styles: dict[str, Any], trace: LayoutTrace):
        self.canvas = canvas
        self.styles = styles
        self.trace = trace
        self.page_no = 0
        self.current_page: PageTrace | None = None
        self.y = 0.0
        self._page_top = 0.0
        self._section_index: int | None = None
        self._section_title = ""
        self._section_subtitle = ""

    @property
    def available_height(self) -> float:
        return max(0.0, self.y - BOTTOM_SAFE)

    def record(
        self,
        kind: str,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        component_type: str | None = None,
        label: str | None = None,
        zone: str = "content",
    ) -> None:
        if self.current_page is None:
            raise RuntimeError("Não há página aberta para registrar o layout.")
        self.current_page.items.append(
            TraceItem(
                kind=kind,
                bbox=BoundingBox(float(x), float(y), float(width), float(height)),
                zone=zone,
                component_type=component_type,
                label=plain_text(label)[:100] if label else None,
            )
        )

    def open_page(
        self,
        role: str,
        *,
        section_index: int | None = None,
        section_title: str | None = None,
    ) -> None:
        if self.current_page is not None:
            raise RuntimeError("Finalize a página atual antes de abrir outra.")
        self.page_no += 1
        self.current_page = PageTrace(
            number=self.page_no,
            role=role,
            section_index=section_index,
            section_title=section_title,
        )
        self.trace.pages.append(self.current_page)

    def finish_page(self, *, footer: bool = True) -> None:
        if self.current_page is None:
            return
        if footer:
            from .section import draw_footer

            draw_footer(self)
        self.canvas.showPage()
        self.current_page = None
        self.y = 0.0

    def start_section(self, section_index: int, title: str, subtitle: str = "") -> None:
        self.finish_page()
        self._section_index = section_index
        self._section_title = plain_text(title)
        self._section_subtitle = plain_text(subtitle)
        self.open_page(
            "section", section_index=section_index, section_title=self._section_title,
        )
        from .section import draw_section_header

        self.y = draw_section_header(
            self, self._section_title, self._section_subtitle, continued=False,
        )
        self._page_top = self.y

    def continuation(self) -> None:
        if self._section_index is None:
            raise RuntimeError("Continuação solicitada fora de uma seção.")
        self.finish_page()
        self.open_page(
            "continuation",
            section_index=self._section_index,
            section_title=self._section_title,
        )
        from .section import draw_section_header

        self.y = draw_section_header(
            self, self._section_title, self._section_subtitle, continued=True,
        )
        self._page_top = self.y

    def start_content(self) -> None:
        """Open the first prose page used by the document-level Markdown mode."""

        self.finish_page()
        self._section_index = None
        self._section_title = ""
        self._section_subtitle = ""
        self.open_page("content")
        from .section import draw_content_header

        self.y = draw_content_header(self)
        self._page_top = self.y

    def continuation_content(self) -> None:
        self.finish_page()
        self.open_page("content")
        from .section import draw_content_header

        self.y = draw_content_header(self)
        self._page_top = self.y

    def draw_blocks(
        self,
        blocks,
        *,
        continuation,
        x: float = MARGIN,
        width: float = CONTENT_WIDTH,
    ) -> None:
        """Lay out Markdown blocks, splitting them across prose pages."""

        pending = list(blocks)
        while pending:
            block = pending[0]
            fresh = abs(self.y - self._page_top) < 0.01
            if not fresh and self.available_height <= 1.0:
                continuation()
                continue

            flowable = block.flowable
            if block.space_before and not fresh and self.available_height >= block.space_before:
                self.y -= block.space_before

            _, height = flowable.wrap(width, PAGE_HEIGHT)
            if (
                block.keep_with_next
                and not fresh
                and self.available_height < height + block.keep_with_next
            ):
                continuation()
                continue

            if height <= self.available_height:
                bottom = self.y - height
                flowable.drawOn(self.canvas, x, bottom)
                self.record(
                    block.kind, x, bottom, width, height,
                    component_type="markdown", label=block.label,
                )
                self.y = max(bottom - block.space_after, BOTTOM_SAFE)
                pending.pop(0)
                continue

            parts = [] if fresh else flowable.split(width, self.available_height)
            if not parts and fresh:
                parts = flowable.split(width, self.available_height)
                if not parts:
                    raise ValueError(
                        "Bloco de Markdown excede a área útil de uma página; "
                        "divida o texto em blocos menores."
                    )
            if not parts:
                continuation()
                continue

            first, *rest = parts
            _, first_height = first.wrap(width, self.available_height)
            bottom = self.y - first_height
            first.drawOn(self.canvas, x, bottom)
            self.record(
                block.kind, x, bottom, width, first_height,
                component_type="markdown", label=block.label,
            )
            self.y = max(bottom, BOTTOM_SAFE)
            if not rest:
                self.y = max(self.y - block.space_after, BOTTOM_SAFE)
                pending.pop(0)
                continue
            pending = [
                block.continuation(
                    part, space_after=block.space_after if offset == len(rest) - 1 else 0.0,
                )
                for offset, part in enumerate(rest)
            ] + pending[1:]
            continuation()

    def ensure_space(self, height: float, *, allow_fresh_page_overflow: bool = False) -> None:
        if height <= self.available_height:
            return
        if self.current_page is None or self.current_page.role not in {"section", "continuation"}:
            raise RuntimeError("Conteúdo fora de uma página de seção.")
        self.continuation()
        if height > self.available_height and not allow_fresh_page_overflow:
            raise ValueError(
                f"Bloco de {height:.1f} pt excede a área útil de uma página; divida o conteúdo."
            )

    def paragraph(self, value: Any, style: str = "body") -> Paragraph:
        return Paragraph(safe_text(value), self.styles[style])

    def paragraph_height(self, value: Any, width: float, style: str = "body") -> float:
        paragraph = self.paragraph(value, style)
        _, height = paragraph.wrap(width, PAGE_HEIGHT)
        return height

    def draw_paragraph_flow(
        self,
        value: Any,
        *,
        width: float = CONTENT_WIDTH,
        x: float = MARGIN,
        style: str = "body",
        component_type: str,
        kind: str = "paragraph",
        gap_after: float = 16,
        label: str | None = None,
    ) -> None:
        pending: list[Any] = [self.paragraph(value, style)]
        while pending:
            flowable = pending.pop(0)
            _, height = flowable.wrap(width, PAGE_HEIGHT)
            if height <= self.available_height:
                bottom = self.y - height
                flowable.drawOn(self.canvas, x, bottom)
                self.record(
                    kind, x, bottom, width, height,
                    component_type=component_type, label=label,
                )
                self.y = bottom - gap_after
                continue

            available = self.available_height
            parts = flowable.split(width, available) if available > 0 else []
            if not parts:
                self.continuation()
                parts = flowable.split(width, self.available_height)
                if not parts:
                    raise ValueError("Texto não pode ser dividido com segurança na área útil.")
            first, *rest = parts
            _, first_height = first.wrap(width, self.available_height)
            bottom = self.y - first_height
            first.drawOn(self.canvas, x, bottom)
            self.record(
                kind, x, bottom, width, first_height,
                component_type=component_type, label=label,
            )
            pending = rest + pending
            if pending:
                self.continuation()
            else:
                self.y = bottom - gap_after
