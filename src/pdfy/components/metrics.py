from __future__ import annotations

from pdfy.design.colors import BLUE, BLUE_SURFACE, DARK, MINT_SURFACE
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import CARD_GAP, BLOCK_GAP
from pdfy.design.styles import rounded_box

from .base import ComponentRenderer, draw_component_title, item_text, items


class MetricsRenderer(ComponentRenderer):
    type_name = "metrics"

    def render(self, component, context) -> None:
        draw_component_title(component, context, self.type_name)
        entries = items(component)
        for start in range(0, len(entries), 3):
            row = entries[start:start + 3]
            width = (CONTENT_WIDTH - CARD_GAP * (len(row) - 1)) / len(row)
            heights = []
            for item in row:
                label = item_text(item, "label", "title", default="MÉTRICA")
                metric = item_text(item, "value", "content")
                note = item_text(item, "note", "description")
                heights.append(
                    max(
                        72,
                        28
                        + context.paragraph_height(label.upper(), width - 26, "label")
                        + context.paragraph_height(metric, width - 26, "h2")
                        + (context.paragraph_height(note, width - 26, "compact") + 8 if note else 0),
                    )
                )
            height = max(heights)
            context.ensure_space(height)
            top = context.y
            for index, item in enumerate(row):
                x = MARGIN + index * (width + CARD_GAP)
                fill = MINT_SURFACE if (start + index) % 3 == 2 else BLUE_SURFACE
                rounded_box(context.canvas, x, top - height, width, height, fill, radius=10)
                cursor = top - 16
                label = item_text(item, "label", "title", default="MÉTRICA").upper()
                metric = item_text(item, "value", "content")
                note = item_text(item, "note", "description")
                p = context.paragraph(label, "label")
                _, ph = p.wrap(width - 26, 60)
                p.drawOn(context.canvas, x + 13, cursor - ph)
                cursor -= ph + 8
                p = context.paragraph(metric, "h2")
                _, ph = p.wrap(width - 26, 100)
                p.drawOn(context.canvas, x + 13, cursor - ph)
                cursor -= ph + 6
                if note:
                    p = context.paragraph(note, "compact")
                    _, ph = p.wrap(width - 26, 160)
                    p.drawOn(context.canvas, x + 13, cursor - ph)
                context.record(
                    "metric", x, top - height, width, height,
                    component_type=self.type_name, label=label,
                )
            context.y = top - height - BLOCK_GAP


RENDERER = MetricsRenderer()
