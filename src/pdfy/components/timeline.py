from __future__ import annotations

from pdfy.design.colors import BLUE, DARK, LINE, MID, SOFT
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import BLOCK_GAP
from pdfy.design.styles import rounded_box
from pdfy.design.typography import FONT_BOLD

from .base import ComponentRenderer, draw_component_title, item_text, items


class TimelineRenderer(ComponentRenderer):
    type_name = "timeline"

    def render(self, component, context) -> None:
        entries = items(component)
        for batch_start in range(0, len(entries), 7):
            batch = entries[batch_start:batch_start + 7]
            row_heights = []
            for item in batch:
                title = item_text(item, "title", "label")
                content = item_text(item, "content", "description", "text")
                row_heights.append(
                    max(
                        68,
                        28
                        + context.paragraph_height(title, CONTENT_WIDTH - 90, "h2")
                        + context.paragraph_height(content, CONTENT_WIDTH - 90, "compact"),
                    )
                )
            total = sum(row_heights) + 10 * max(0, len(batch) - 1)
            component_title = str(component.get("title", "")) if hasattr(component, "get") else ""
            title_h = context.paragraph_height(component_title, CONTENT_WIDTH, "h2") + 12 if component_title else 0
            if batch_start or (
                total + title_h > context.available_height
                and total + title_h <= 560
            ):
                context.continuation()
            draw_component_title(
                component,
                context,
                self.type_name,
                keep_with=min(total, 500),
            )
            context.ensure_space(total)
            cursor = context.y
            line_x = MARGIN + 20
            context.canvas.setStrokeColor(LINE)
            context.canvas.setLineWidth(1.2)
            context.canvas.line(line_x, cursor - 18, line_x, cursor - total + 18)
            for offset, (item, height) in enumerate(zip(batch, row_heights)):
                title = item_text(item, "title", "label")
                content = item_text(item, "content", "description", "text")
                marker = item_text(item, "date", "period", "number", default=f"{batch_start + offset + 1:02d}")
                bottom = cursor - height
                rounded_box(context.canvas, MARGIN + 48, bottom, CONTENT_WIDTH - 48, height, SOFT, radius=10)
                context.canvas.setFillColor(BLUE if offset < len(batch) - 1 else DARK)
                context.canvas.circle(line_x, cursor - 24, 7, fill=1, stroke=0)
                marker_p = context.paragraph(marker.upper(), "label")
                _, marker_h = marker_p.wrap(CONTENT_WIDTH - 82, 30)
                marker_p.drawOn(context.canvas, MARGIN + 64, cursor - 14 - marker_h)
                title_p = context.paragraph(title, "h2")
                _, title_h = title_p.wrap(CONTENT_WIDTH - 82, 80)
                title_p.drawOn(context.canvas, MARGIN + 64, cursor - 30 - title_h)
                if content:
                    body_p = context.paragraph(content, "compact")
                    _, body_h = body_p.wrap(CONTENT_WIDTH - 82, 180)
                    body_p.drawOn(context.canvas, MARGIN + 64, bottom + 13)
                context.record(
                    "timeline-item", MARGIN, bottom, CONTENT_WIDTH, height,
                    component_type=self.type_name, label=title,
                )
                cursor = bottom - 10
            context.y = cursor - BLOCK_GAP + 10


RENDERER = TimelineRenderer()
