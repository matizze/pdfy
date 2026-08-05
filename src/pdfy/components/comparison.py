from __future__ import annotations

from pdfy.design.colors import BLUE, BLUE_SURFACE, DARK, MINT, MINT_SURFACE
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import BLOCK_GAP, CARD_GAP
from pdfy.design.styles import rounded_box

from .base import ComponentRenderer, draw_component_title, item_text, items, value


class ComparisonRenderer(ComponentRenderer):
    type_name = "comparison"

    def render(self, component, context) -> None:
        rows = items(component, "rows")
        left_label = str(value(component, "left_label", "PONTO A"))
        right_label = str(value(component, "right_label", "PONTO B"))
        width = (CONTENT_WIDTH - CARD_GAP) / 2
        row_specs = []
        for row in rows:
            label = item_text(row, "label")
            left = item_text(row, "left")
            right = item_text(row, "right")
            label_h = context.paragraph_height(label, CONTENT_WIDTH, "label")
            left_h = context.paragraph_height(left, width - 28, "compact")
            right_h = context.paragraph_height(right, width - 28, "compact")
            cell_h = max(58, max(left_h, right_h) + 28)
            row_specs.append((row, label, left, right, label_h, cell_h))
        title = str(value(component, "title", ""))
        title_h = context.paragraph_height(title, CONTENT_WIDTH, "h2") + 12 if title else 0
        full_height = title_h + 44 + sum(spec[4] + 8 + spec[5] + BLOCK_GAP for spec in row_specs)
        if full_height > context.available_height and full_height <= 540:
            context.continuation()
        first_height = row_specs[0][4] + 8 + row_specs[0][5] if row_specs else 0
        draw_component_title(component, context, self.type_name, keep_with=44 + first_height)
        self._draw_headers(context, left_label, right_label, width)

        for row, label, left, right, label_h, cell_h in row_specs:
            needed = label_h + 8 + cell_h
            if needed > context.available_height:
                context.continuation()
                draw_component_title(component, context, self.type_name, keep_with=44 + needed)
                self._draw_headers(context, left_label, right_label, width)
            top = context.y
            label_p = context.paragraph(label.upper(), "label")
            label_p.wrap(CONTENT_WIDTH, 30)
            label_p.drawOn(context.canvas, MARGIN, top - label_h)
            cell_top = top - label_h - 8
            for column, (content, fill, accent) in enumerate((
                (left, BLUE_SURFACE, BLUE),
                (right, MINT_SURFACE, MINT),
            )):
                x = MARGIN + column * (width + CARD_GAP)
                bottom = cell_top - cell_h
                rounded_box(context.canvas, x, bottom, width, cell_h, fill, radius=9)
                context.canvas.setFillColor(accent)
                context.canvas.rect(x, bottom, 4, cell_h, fill=1, stroke=0)
                paragraph = context.paragraph(content, "compact")
                _, paragraph_h = paragraph.wrap(width - 28, cell_h - 24)
                paragraph.drawOn(context.canvas, x + 14, cell_top - 14 - paragraph_h)
                context.record(
                    "comparison-cell", x, bottom, width, cell_h,
                    component_type=self.type_name, label=label,
                )
            context.y = cell_top - cell_h - BLOCK_GAP

    def _draw_headers(self, context, left_label: str, right_label: str, width: float) -> None:
        header_h = 34
        context.ensure_space(header_h)
        top = context.y
        for column, (label, fill) in enumerate((
            (left_label, BLUE_SURFACE),
            (right_label, MINT_SURFACE),
        )):
            x = MARGIN + column * (width + CARD_GAP)
            rounded_box(context.canvas, x, top - header_h, width, header_h, fill, radius=10)
            paragraph = context.paragraph(label.upper(), "label")
            _, height = paragraph.wrap(width - 24, 24)
            paragraph.drawOn(context.canvas, x + 12, top - 11 - height)
            context.record(
                "comparison-header", x, top - header_h, width, header_h,
                component_type=self.type_name, label=label,
            )
        context.y = top - header_h - 10


RENDERER = ComparisonRenderer()
