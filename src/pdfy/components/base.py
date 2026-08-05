"""Shared component primitives."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from pdfy.design.colors import BLUE, DARK, MINT, SOFT, WHITE
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN, PAGE_HEIGHT
from pdfy.design.spacing import BLOCK_GAP, CARD_RADIUS
from pdfy.design.styles import rounded_box
from pdfy.template.paginator import RenderContext, plain_text, safe_text


def value(obj: Any, name: str, default=None):
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def items(component: Any, name: str = "items") -> list[Any]:
    raw = value(component, name, ()) or ()
    if isinstance(raw, (str, bytes)):
        return [raw]
    return list(raw)


def item_text(item: Any, *keys: str, default: str = "") -> str:
    if isinstance(item, Mapping):
        for key in keys:
            candidate = item.get(key)
            if candidate not in (None, ""):
                return plain_text(candidate)
        return default
    return plain_text(item)


class ComponentRenderer(ABC):
    type_name: str

    @abstractmethod
    def render(self, component: Any, context: RenderContext) -> None:
        raise NotImplementedError


def draw_component_title(
    component: Any,
    context: RenderContext,
    component_type: str,
    *,
    keep_with: float = 72,
) -> None:
    title = plain_text(value(component, "title", ""))
    if not title:
        return
    height = context.paragraph_height(title, CONTENT_WIDTH, "h2")
    context.ensure_space(height + 12 + keep_with)
    bottom = context.y - height
    paragraph = context.paragraph(title, "h2")
    paragraph.wrap(CONTENT_WIDTH, height)
    paragraph.drawOn(context.canvas, MARGIN, bottom)
    context.record(
        "component-title", MARGIN, bottom, CONTENT_WIDTH, height,
        component_type=component_type, label=title,
    )
    context.y = bottom - 12


def draw_card(
    context: RenderContext,
    *,
    x: float,
    y_top: float,
    width: float,
    title: str,
    content: str,
    component_type: str,
    label: str = "",
    accent=BLUE,
    fill=SOFT,
    min_height: float = 96,
) -> float:
    title_h = context.paragraph_height(title, width - 32, "h2") if title else 0
    content_h = context.paragraph_height(content, width - 32, "compact") if content else 0
    label_h = context.paragraph_height(label.upper(), width - 32, "label") if label else 0
    height = max(min_height, 28 + label_h + title_h + content_h + (10 if title and content else 0))
    context.ensure_space(height)
    y_top = context.y if y_top > context.y else y_top
    bottom = y_top - height
    rounded_box(context.canvas, x, bottom, width, height, fill, radius=CARD_RADIUS)
    context.canvas.setFillColor(accent)
    context.canvas.rect(x, bottom, 4, height, fill=1, stroke=0)
    cursor = y_top - 16
    if label:
        p = context.paragraph(label.upper(), "label")
        _, ph = p.wrap(width - 32, 80)
        p.drawOn(context.canvas, x + 16, cursor - ph)
        cursor -= ph + 10
    if title:
        p = context.paragraph(title, "h2")
        _, ph = p.wrap(width - 32, 160)
        p.drawOn(context.canvas, x + 16, cursor - ph)
        cursor -= ph + 10
    if content:
        p = context.paragraph(content, "compact")
        _, ph = p.wrap(width - 32, PAGE_HEIGHT)
        p.drawOn(context.canvas, x + 16, cursor - ph)
    context.record(
        "card", x, bottom, width, height,
        component_type=component_type, label=title or label,
    )
    return height


def draw_dark_panel(
    context: RenderContext,
    *,
    title: str,
    content: str,
    component_type: str,
) -> None:
    """Draw a callout, splitting its body into continued panels when necessary."""
    pending = context.paragraph(content, "white_body")
    first = True
    while pending is not None:
        label = title if first else f"{title} - CONTINUAÇÃO"
        label_h = context.paragraph_height(label.upper(), CONTENT_WIDTH - 36, "label")
        max_body = max(1, context.available_height - label_h - 42)
        parts = pending.split(CONTENT_WIDTH - 36, max_body)
        if not parts:
            context.continuation()
            continue
        body = parts[0]
        rest = parts[1] if len(parts) > 1 else None
        _, body_h = body.wrap(CONTENT_WIDTH - 36, max_body)
        height = max(72, label_h + body_h + 38)
        context.ensure_space(height)
        bottom = context.y - height
        rounded_box(context.canvas, MARGIN, bottom, CONTENT_WIDTH, height, DARK, radius=12)
        label_style = ParagraphStyle(
            f"{component_type}-callout-label",
            parent=context.styles["label"],
            textColor=MINT,
        )
        label_p = Paragraph(safe_text(label.upper()), label_style)
        _, actual_label_h = label_p.wrap(CONTENT_WIDTH - 36, 80)
        label_p.drawOn(context.canvas, MARGIN + 18, context.y - 18 - actual_label_h)
        body.drawOn(context.canvas, MARGIN + 18, bottom + 16)
        context.record(
            "callout", MARGIN, bottom, CONTENT_WIDTH, height,
            component_type=component_type, label=title,
        )
        context.y = bottom - BLOCK_GAP
        pending = rest
        first = False
        if pending is not None:
            context.continuation()
