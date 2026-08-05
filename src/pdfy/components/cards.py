from __future__ import annotations

from pdfy.design.colors import BLUE, MINT
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import BLOCK_GAP, CARD_GAP

from .base import ComponentRenderer, draw_card, draw_component_title, item_text, items


class CardsRenderer(ComponentRenderer):
    type_name = "cards"

    def render(self, component, context) -> None:
        draw_component_title(component, context, self.type_name)
        entries = items(component)
        width = (CONTENT_WIDTH - CARD_GAP) / 2
        for start in range(0, len(entries), 2):
            row = entries[start:start + 2]
            specs = []
            for item in row:
                label = item_text(item, "label", "tag", default=f"ITEM {start + len(specs) + 1:02d}")
                title = item_text(item, "title", "heading")
                content = item_text(item, "content", "description", "text")
                height = max(
                    102,
                    28
                    + context.paragraph_height(label.upper(), width - 32, "label")
                    + context.paragraph_height(title, width - 32, "h2")
                    + context.paragraph_height(content, width - 32, "compact")
                    + 18,
                )
                specs.append((label, title, content, height))
            row_height = max(spec[3] for spec in specs)
            context.ensure_space(row_height)
            top = context.y
            for col, (label, title, content, _) in enumerate(specs):
                draw_card(
                    context,
                    x=MARGIN + col * (width + CARD_GAP),
                    y_top=top,
                    width=width,
                    title=title,
                    content=content,
                    component_type=self.type_name,
                    label=label,
                    accent=BLUE if (start + col) % 2 == 0 else MINT,
                    min_height=row_height,
                )
            context.y = top - row_height - BLOCK_GAP


RENDERER = CardsRenderer()
