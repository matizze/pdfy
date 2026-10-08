"""High-level orchestration of the one official document template."""

from __future__ import annotations

from collections.abc import Mapping

from pdfy.registry import get_renderer

from .closing import draw_closing
from .cover import draw_cover
from .paginator import LayoutTrace, RenderContext


def value(obj, name: str, default=None):
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


class DocumentRenderer:
    def __init__(self, canvas, styles: dict):
        self.trace = LayoutTrace()
        self.context = RenderContext(canvas, styles, self.trace)

    def render(self, document) -> LayoutTrace:
        draw_cover(self.context, document)
        content = value(document, "content", None)
        if content:
            self._render_markdown(str(content))
        else:
            sections = value(document, "sections", ()) or ()
            for section_index, section in enumerate(sections):
                title = value(section, "title", f"Seção {section_index + 1}")
                subtitle = value(section, "subtitle", "")
                self.context.start_section(section_index, title, subtitle)
                components = value(section, "components", ()) or ()
                for component in components:
                    component_type = str(value(component, "type", "")).lower()
                    renderer = get_renderer(component_type)
                    renderer.render(component, self.context)
        draw_closing(self.context)
        return self.trace

    def _render_markdown(self, content: str) -> None:
        from pdfy.markdown import render_markdown

        blocks = render_markdown(content, self.context.styles)
        self.context.start_content()
        self.context.draw_blocks(blocks, continuation=self.context.continuation_content)
