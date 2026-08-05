from __future__ import annotations

from .base import ComponentRenderer, draw_dark_panel, value


class CalloutRenderer(ComponentRenderer):
    type_name = "callout"

    def render(self, component, context) -> None:
        draw_dark_panel(
            context,
            title=value(component, "title", "EM DESTAQUE") or "EM DESTAQUE",
            content=value(component, "content", ""),
            component_type=self.type_name,
        )


RENDERER = CalloutRenderer()
