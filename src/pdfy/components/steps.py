from __future__ import annotations

from pdfy.design.colors import BLUE, BLUE_SURFACE, DARK, WHITE
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import BLOCK_GAP
from pdfy.design.styles import rounded_box
from pdfy.design.typography import FONT_BOLD

from .base import ComponentRenderer, draw_component_title, item_text, items


class StepsRenderer(ComponentRenderer):
    type_name = "steps"

    def render(self, component, context) -> None:
        draw_component_title(component, context, self.type_name)
        for index, item in enumerate(items(component), 1):
            title = item_text(item, "title", "label")
            content = item_text(item, "content", "description", "text")
            text_width = CONTENT_WIDTH - 70
            height = max(
                76,
                30
                + context.paragraph_height(title, text_width, "h2")
                + context.paragraph_height(content, text_width, "compact"),
            )
            context.ensure_space(height)
            top, bottom = context.y, context.y - height
            rounded_box(context.canvas, MARGIN, bottom, CONTENT_WIDTH, height, BLUE_SURFACE, radius=10)
            rounded_box(context.canvas, MARGIN + 14, top - 49, 34, 34, BLUE, radius=17)
            context.canvas.setFillColor(WHITE)
            context.canvas.setFont(FONT_BOLD, 9)
            context.canvas.drawCentredString(MARGIN + 31, top - 37, f"{index:02d}")
            cursor = top - 16
            title_p = context.paragraph(title, "h2")
            _, title_h = title_p.wrap(text_width, 100)
            title_p.drawOn(context.canvas, MARGIN + 58, cursor - title_h)
            cursor -= title_h + 8
            body_p = context.paragraph(content, "compact")
            _, body_h = body_p.wrap(text_width, 300)
            body_p.drawOn(context.canvas, MARGIN + 58, cursor - body_h)
            context.record(
                "step", MARGIN, bottom, CONTENT_WIDTH, height,
                component_type=self.type_name, label=title,
            )
            context.y = bottom - BLOCK_GAP


RENDERER = StepsRenderer()
