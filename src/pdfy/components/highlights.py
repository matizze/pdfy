from __future__ import annotations

from pdfy.design.colors import BLUE, MINT
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import BLOCK_GAP, CARD_GAP

from .base import ComponentRenderer, draw_card, draw_component_title, item_text, items


class HighlightsRenderer(ComponentRenderer):
    type_name = "highlights"

    def render(self, component, context) -> None:
        draw_component_title(component, context, self.type_name)
        entries = items(component)
        width = (CONTENT_WIDTH - CARD_GAP) / 2
        for start in range(0, len(entries), 2):
            row = entries[start:start + 2]
            heights = []
            for item in row:
                title = item_text(item, "title", "label") if hasattr(item, "get") else ""
                content = item_text(item, "content", "description", "text")
                heights.append(
                    max(
                        92,
                        38
                        + context.paragraph_height(title, width - 32, "h2")
                        + context.paragraph_height(content, width - 32, "compact"),
                    )
                )
            row_height = max(heights)
            context.ensure_space(row_height)
            top = context.y
            for col, item in enumerate(row):
                draw_card(
                    context,
                    x=MARGIN + col * (width + CARD_GAP),
                    y_top=top,
                    width=width,
                    title=item_text(item, "title", "label") if hasattr(item, "get") else "",
                    content=item_text(item, "content", "description", "text"),
                    component_type=self.type_name,
                    label="DESTAQUE",
                    accent=BLUE if (start + col) % 2 == 0 else MINT,
                    min_height=row_height,
                )
            context.y = top - row_height - BLOCK_GAP


RENDERER = HighlightsRenderer()
