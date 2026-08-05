from __future__ import annotations

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from pdfy.design.colors import DARK, MINT, SOFT, WHITE
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import BLOCK_GAP, CARD_GAP
from pdfy.design.styles import rounded_box
from pdfy.template.paginator import safe_text

from .base import ComponentRenderer, draw_component_title, item_text, items, value


class InvestmentRenderer(ComponentRenderer):
    type_name = "investment"

    def render(self, component, context) -> None:
        draw_component_title(component, context, self.type_name)
        total = value(component, "total")
        if total:
            self._draw_total(total, context)

        entries = items(component)
        width = (CONTENT_WIDTH - CARD_GAP) / 2
        for start in range(0, len(entries), 2):
            row = entries[start:start + 2]
            heights = []
            for item in row:
                label = item_text(item, "label")
                amount = item_text(item, "value")
                description = item_text(item, "description")
                heights.append(max(
                    96,
                    34
                    + context.paragraph_height(label, width - 28, "label")
                    + context.paragraph_height(amount, width - 28, "h2")
                    + (context.paragraph_height(description, width - 28, "compact") + 8 if description else 0),
                ))
            height = max(heights)
            context.ensure_space(height)
            top = context.y
            for column, item in enumerate(row):
                x = MARGIN + column * (width + CARD_GAP)
                bottom = top - height
                rounded_box(context.canvas, x, bottom, width, height, SOFT, radius=10)
                cursor = top - 15
                label = item_text(item, "label")
                amount = item_text(item, "value")
                description = item_text(item, "description")
                p = context.paragraph(label.upper(), "label")
                _, ph = p.wrap(width - 28, 50)
                p.drawOn(context.canvas, x + 14, cursor - ph)
                cursor -= ph + 9
                p = context.paragraph(amount, "h2")
                _, ph = p.wrap(width - 28, 60)
                p.drawOn(context.canvas, x + 14, cursor - ph)
                cursor -= ph + 8
                if description:
                    p = context.paragraph(description, "compact")
                    _, ph = p.wrap(width - 28, 160)
                    p.drawOn(context.canvas, x + 14, cursor - ph)
                context.record(
                    "investment-item", x, bottom, width, height,
                    component_type=self.type_name, label=label,
                )
            context.y = top - height - BLOCK_GAP

        notes = items(component, "notes")
        if notes:
            context.ensure_space(context.paragraph_height("PREMISSAS", CONTENT_WIDTH, "label") + 10)
            p = context.paragraph("PREMISSAS", "label")
            _, h = p.wrap(CONTENT_WIDTH, 30)
            p.drawOn(context.canvas, MARGIN, context.y - h)
            context.y -= h + 10
        for note in notes:
            height = max(44, context.paragraph_height(note, CONTENT_WIDTH - 34, "compact") + 22)
            context.ensure_space(height)
            bottom = context.y - height
            rounded_box(context.canvas, MARGIN, bottom, CONTENT_WIDTH, height, SOFT, radius=9)
            p = context.paragraph(note, "compact")
            _, ph = p.wrap(CONTENT_WIDTH - 34, height - 18)
            p.drawOn(context.canvas, MARGIN + 17, bottom + (height - ph) / 2)
            context.record(
                "investment-note", MARGIN, bottom, CONTENT_WIDTH, height,
                component_type=self.type_name, label="Premissa",
            )
            context.y = bottom - 10
        if notes:
            context.y -= max(0, BLOCK_GAP - 10)

    def _draw_total(self, total, context) -> None:
        label = item_text(total, "label", default="TOTAL")
        amount = item_text(total, "value")
        amount_h = context.paragraph_height(amount, CONTENT_WIDTH - 36, "page_title")
        height = max(104, 58 + amount_h)
        context.ensure_space(height)
        top, bottom = context.y, context.y - height
        rounded_box(context.canvas, MARGIN, bottom, CONTENT_WIDTH, height, DARK, radius=12)
        label_p = Paragraph(
            safe_text(label.upper()),
            ParagraphStyle("InvestmentTotalLabel", parent=context.styles["label"], textColor=MINT),
        )
        _, label_h = label_p.wrap(CONTENT_WIDTH - 36, 30)
        label_p.drawOn(context.canvas, MARGIN + 18, top - 18 - label_h)
        amount_p = Paragraph(
            safe_text(amount),
            ParagraphStyle("InvestmentTotalAmount", parent=context.styles["page_title"], textColor=WHITE),
        )
        _, amount_h = amount_p.wrap(CONTENT_WIDTH - 36, 70)
        amount_p.drawOn(context.canvas, MARGIN + 18, bottom + 18)
        context.record(
            "investment-total", MARGIN, bottom, CONTENT_WIDTH, height,
            component_type=self.type_name, label=label,
        )
        context.y = bottom - BLOCK_GAP


RENDERER = InvestmentRenderer()
