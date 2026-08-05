from __future__ import annotations

from pdfy.design.colors import BLUE, BLUE_SURFACE, INK
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import BLOCK_GAP
from pdfy.design.styles import rounded_box
from pdfy.design.typography import FONT_BOLD

from .base import ComponentRenderer, draw_component_title, item_text, items, value


class ListRenderer(ComponentRenderer):
    type_name = "list"

    def render(self, component, context) -> None:
        entries = items(component)
        ordered = bool(value(component, "ordered", False))
        specs = []
        for item in entries:
            title = item_text(item, "title", "label")
            content = item_text(item, "content", "description", "text", default=title)
            if title == content:
                title = ""
            text_width = CONTENT_WIDTH - 54
            height = max(
                54,
                24
                + context.paragraph_height(title, text_width, "h2")
                + context.paragraph_height(content, text_width, "compact"),
            )
            specs.append((item, title, content, text_width, height))
        component_title = str(value(component, "title", ""))
        title_h = context.paragraph_height(component_title, CONTENT_WIDTH, "h2") + 12 if component_title else 0
        full_height = title_h + sum(spec[4] + 10 for spec in specs) + BLOCK_GAP
        if full_height > context.available_height and full_height <= 540:
            context.continuation()
        draw_component_title(
            component, context, self.type_name,
            keep_with=specs[0][4] if specs else 0,
        )
        for index, (_, title, content, text_width, height) in enumerate(specs, 1):
            context.ensure_space(height)
            top, bottom = context.y, context.y - height
            rounded_box(context.canvas, MARGIN, bottom, CONTENT_WIDTH, height, BLUE_SURFACE, radius=9)
            context.canvas.setFillColor(BLUE)
            if ordered:
                context.canvas.setFont(FONT_BOLD, 8)
                context.canvas.drawCentredString(MARGIN + 22, top - 29, f"{index:02d}")
            else:
                context.canvas.circle(MARGIN + 22, top - 26, 3.5, fill=1, stroke=0)
            cursor = top - 14
            if title:
                p = context.paragraph(title, "h2")
                _, ph = p.wrap(text_width, 80)
                p.drawOn(context.canvas, MARGIN + 42, cursor - ph)
                cursor -= ph + 6
            p = context.paragraph(content, "compact")
            _, ph = p.wrap(text_width, 200)
            p.drawOn(context.canvas, MARGIN + 42, cursor - ph)
            context.record(
                "list-item", MARGIN, bottom, CONTENT_WIDTH, height,
                component_type=self.type_name, label=title or content,
            )
            context.y = bottom - 10
        context.y -= max(0, BLOCK_GAP - 10)


RENDERER = ListRenderer()
