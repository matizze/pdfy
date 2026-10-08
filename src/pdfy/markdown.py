"""Convert a Markdown document into styled, paginatable ReportLab blocks."""

from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

from markdown_it import MarkdownIt
from markdown_it.token import Token
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Table, TableStyle

from pdfy.design.colors import LINE, SOFT
from pdfy.design.dimensions import CONTENT_WIDTH
from pdfy.design.typography import FONT_REGULAR, FONT_SEMIBOLD

BODY_SPACE = 9.0
HEADING_SPACE_BEFORE = 16.0
HEADING_SPACE_AFTER = 7.0
LIST_SPACE = 4.0
CODE_SPACE_BEFORE = 10.0
RULE_SPACE = 12.0
TABLE_SPACE_BEFORE = 10.0
TABLE_PADDING = 6.0
LIST_INDENT = 16.0


@dataclass
class MarkdownBlock:
    """One splittable piece of a Markdown document, with vertical spacing."""

    flowable: Flowable
    kind: str = "markdown"
    space_before: float = 0.0
    space_after: float = BODY_SPACE
    keep_with_next: float = 0.0
    label: str | None = None

    def continuation(self, flowable: Flowable, *, space_after: float = 0.0) -> MarkdownBlock:
        return MarkdownBlock(
            flowable=flowable,
            kind=self.kind,
            space_before=0.0,
            space_after=space_after,
            keep_with_next=0.0,
            label=self.label,
        )


def _text(value: str) -> str:
    return (
        str(value)
        .replace("–", "-")
        .replace("—", "-")
        .replace("‑", "-")
        .replace("\u00a0", " ")
    )


def _inline(token: Token) -> str:
    parts: list[str] = []
    for child in token.children or []:
        kind = child.type
        if kind == "text":
            parts.append(escape(_text(child.content)))
        elif kind == "softbreak":
            parts.append(" ")
        elif kind == "hardbreak":
            parts.append("<br/>")
        elif kind == "strong_open":
            parts.append("<b>")
        elif kind == "strong_close":
            parts.append("</b>")
        elif kind == "em_open":
            parts.append("<i>")
        elif kind == "em_close":
            parts.append("</i>")
        elif kind == "s_open":
            parts.append("<strike>")
        elif kind == "s_close":
            parts.append("</strike>")
        elif kind == "code_inline":
            parts.append(f'<font name="{FONT_SEMIBOLD}">{escape(_text(child.content))}</font>')
        elif kind == "link_open":
            href = escape(str(child.attrGet("href") or ""), {'"': "&quot;"})
            parts.append(f'<a href="{href}" color="#0033FF">')
        elif kind == "link_close":
            parts.append("</a>")
        elif kind == "image":
            alt = escape(_text(child.content))
            if alt:
                parts.append(f"<i>{alt}</i>")
        elif child.content:
            parts.append(escape(_text(child.content)))
    return "".join(parts)


def _plain_inline(token: Token) -> str:
    return "".join(_text(child.content) for child in (token.children or []) if child.content).strip()


def _list_style(styles: dict, level: int) -> ParagraphStyle:
    base = styles["md_body"]
    return ParagraphStyle(
        f"PdfyMdList{level}",
        parent=base,
        leftIndent=LIST_INDENT + level * LIST_INDENT,
        bulletIndent=2 + level * LIST_INDENT,
        bulletFontName=FONT_REGULAR,
        bulletFontSize=base.fontSize,
        spaceAfter=0,
    )


def _code_block(code: str, styles: dict) -> Paragraph:
    markup = escape(code.replace("\t", "    "))
    markup = markup.replace(" ", "&nbsp;").replace("\n", "<br/>")
    return Paragraph(markup or "&nbsp;", styles["md_code"])


def _alignment(raw: str | None):
    value = (raw or "").lower()
    if "center" in value:
        return TA_CENTER
    if "right" in value:
        return TA_RIGHT
    return TA_LEFT


def _cell_style(styles: dict, header: bool, alignment) -> ParagraphStyle:
    base = styles["md_table_head" if header else "md_table_cell"]
    if alignment == TA_LEFT:
        return base
    return ParagraphStyle(
        f"{base.name}-{int(alignment)}",
        parent=base,
        alignment=alignment,
    )


def _build_table(tokens: list[Token], index: int, styles: dict) -> tuple[Table, int]:
    rows: list[list[str]] = []
    header_rows = 0
    alignments: list[list] = []
    current: list[str] | None = None
    current_align: list | None = None
    in_header = False
    pending_align = TA_LEFT

    index += 1  # table_open
    while index < len(tokens) and tokens[index].type != "table_close":
        kind = tokens[index].type
        if kind == "thead_open":
            in_header = True
        elif kind == "thead_close":
            in_header = False
        elif kind == "tr_open":
            current, current_align = [], []
        elif kind == "tr_close" and current is not None:
            rows.append(current)
            alignments.append(current_align or [])
            if in_header:
                header_rows += 1
            current, current_align = None, None
        elif kind in ("th_open", "td_open"):
            pending_align = _alignment(tokens[index].attrGet("style"))
        elif kind == "inline" and current is not None:
            current.append(_inline(tokens[index]))
            if current_align is not None:
                current_align.append(pending_align)
        index += 1
    index += 1  # table_close

    columns = max((len(row) for row in rows), default=0)
    if columns == 0:
        return Table([[""]]), index

    data: list[list[Paragraph]] = []
    for row_index, row in enumerate(rows):
        is_header = row_index < header_rows
        cells: list[Paragraph] = []
        for column in range(columns):
            markup = row[column] if column < len(row) else ""
            alignment = TA_LEFT
            if row_index < len(alignments) and column < len(alignments[row_index]):
                alignment = alignments[row_index][column]
            cells.append(Paragraph(markup, _cell_style(styles, is_header, alignment)))
        data.append(cells)

    width = CONTENT_WIDTH / columns
    table = Table(data, colWidths=[width] * columns, repeatRows=header_rows)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), TABLE_PADDING),
                ("RIGHTPADDING", (0, 0), (-1, -1), TABLE_PADDING),
                ("TOPPADDING", (0, 0), (-1, -1), TABLE_PADDING),
                ("BOTTOMPADDING", (0, 0), (-1, -1), TABLE_PADDING),
            ]
        )
    )
    if header_rows:
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, header_rows - 1), SOFT)]))
    return table, index


def _list(
    tokens: list[Token], index: int, styles: dict, level: int,
) -> tuple[list[MarkdownBlock], int]:
    ordered = tokens[index].type == "ordered_list_open"
    close = "ordered_list_close" if ordered else "bullet_list_close"
    counter = int(tokens[index].attrGet("start") or 1)
    blocks: list[MarkdownBlock] = []
    index += 1
    while index < len(tokens) and tokens[index].type != close:
        if tokens[index].type != "list_item_open":
            index += 1
            continue
        index += 1
        first = True
        while index < len(tokens) and tokens[index].type != "list_item_close":
            kind = tokens[index].type
            if kind == "paragraph_open":
                markup = _inline(tokens[index + 1])
                if markup.strip():
                    if first:
                        bullet = f"{counter}." if ordered else "\u2022"
                        paragraph = Paragraph(markup, _list_style(styles, level), bulletText=bullet)
                        blocks.append(
                            MarkdownBlock(
                                paragraph, kind="markdown-list",
                                space_before=0.0, space_after=LIST_SPACE,
                            )
                        )
                        first = False
                    else:
                        paragraph = Paragraph(markup, _list_style(styles, level))
                        blocks.append(
                            MarkdownBlock(
                                paragraph, kind="markdown-list",
                                space_before=0.0, space_after=LIST_SPACE,
                            )
                        )
                index += 3
            elif kind in ("bullet_list_open", "ordered_list_open"):
                nested, index = _list(tokens, index, styles, level + 1)
                blocks.extend(nested)
            else:
                index += 1
        # skip list_item_close
        index += 1
        if ordered:
            counter += 1
    index += 1  # list_close
    return blocks, index


def _quote(
    tokens: list[Token], index: int, styles: dict, level: int,
) -> tuple[list[MarkdownBlock], int]:
    blocks: list[MarkdownBlock] = []
    index += 1  # blockquote_open
    while index < len(tokens) and tokens[index].type != "blockquote_close":
        kind = tokens[index].type
        if kind == "paragraph_open":
            markup = _inline(tokens[index + 1])
            if markup.strip():
                blocks.append(
                    MarkdownBlock(
                        Paragraph(markup, styles["md_quote"]), kind="markdown-quote",
                        space_before=0.0 if blocks else 4.0, space_after=BODY_SPACE,
                    )
                )
            index += 3
        elif kind in ("bullet_list_open", "ordered_list_open"):
            nested, index = _list(tokens, index, styles, level)
            blocks.extend(nested)
        else:
            index += 1
    index += 1  # blockquote_close
    return blocks, index


def _blocks(
    tokens: list[Token], index: int, styles: dict, level: int,
) -> tuple[list[MarkdownBlock], int]:
    blocks: list[MarkdownBlock] = []
    while index < len(tokens):
        token = tokens[index]
        kind = token.type
        if kind == "heading_open":
            depth = min(int(token.tag[1]), 4)
            inline = tokens[index + 1]
            label = _plain_inline(inline)
            blocks.append(
                MarkdownBlock(
                    Paragraph(_inline(inline), styles[f"md_h{depth}"]),
                    kind="markdown-heading",
                    space_before=HEADING_SPACE_BEFORE if blocks else 0.0,
                    space_after=HEADING_SPACE_AFTER,
                    keep_with_next=46.0,
                    label=label or None,
                )
            )
            index += 3
        elif kind == "paragraph_open":
            markup = _inline(tokens[index + 1])
            if markup.strip():
                blocks.append(
                    MarkdownBlock(
                        Paragraph(markup, styles["md_body"]),
                        kind="markdown", space_after=BODY_SPACE,
                    )
                )
            index += 3
        elif kind in ("bullet_list_open", "ordered_list_open"):
            listed, index = _list(tokens, index, styles, level)
            blocks.extend(listed)
        elif kind == "blockquote_open":
            quoted, index = _quote(tokens, index, styles, level)
            blocks.extend(quoted)
        elif kind in ("fence", "code_block"):
            blocks.append(
                MarkdownBlock(
                    _code_block(token.content.rstrip("\n"), styles),
                    kind="markdown-code",
                    space_before=CODE_SPACE_BEFORE, space_after=BODY_SPACE,
                )
            )
            index += 1
        elif kind == "hr":
            blocks.append(
                MarkdownBlock(
                    HRFlowable(width="100%", thickness=0.8, color=LINE),
                    kind="markdown-rule",
                    space_before=RULE_SPACE, space_after=RULE_SPACE,
                )
            )
            index += 1
        elif kind == "table_open":
            table, index = _build_table(tokens, index, styles)
            blocks.append(
                MarkdownBlock(
                    table, kind="markdown-table",
                    space_before=TABLE_SPACE_BEFORE, space_after=BODY_SPACE,
                )
            )
        else:
            index += 1
    return blocks, index


def render_markdown(content: str, styles: dict) -> list[MarkdownBlock]:
    """Parse Markdown and return an ordered list of paginatable blocks."""

    parser = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
    tokens = parser.parse(_text(content))
    blocks, _ = _blocks(tokens, 0, styles, level=0)
    return blocks


__all__ = ["MarkdownBlock", "render_markdown"]
