from __future__ import annotations

import re

from .base import ComponentRenderer, draw_component_title, value


class TextRenderer(ComponentRenderer):
    type_name = "text"

    def render(self, component, context) -> None:
        draw_component_title(component, context, self.type_name)
        content = value(component, "content", "")
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", str(content)) if part.strip()]
        for paragraph in paragraphs:
            context.draw_paragraph_flow(
                paragraph, component_type=self.type_name, kind="text", gap_after=16,
            )


RENDERER = TextRenderer()
