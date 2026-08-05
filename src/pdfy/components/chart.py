from __future__ import annotations

from pdfy.design.colors import BLUE, BLUE_2, DARK, MID, SOFT
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN, PAGE_WIDTH
from pdfy.design.spacing import BLOCK_GAP
from pdfy.design.styles import rounded_box
from pdfy.design.typography import FONT_MEDIUM, FONT_REGULAR, FONT_SEMIBOLD

from .base import ComponentRenderer, draw_component_title, item_text, items, value


class ChartRenderer(ComponentRenderer):
    type_name = "chart"

    def render(self, component, context) -> None:
        draw_component_title(component, context, self.type_name)
        entries = items(component)
        unit = str(value(component, "unit", ""))
        for batch_start in range(0, len(entries), 8):
            batch = entries[batch_start:batch_start + 8]
            if batch_start:
                context.continuation()
            values = []
            for item in batch:
                raw = item.get("value", 0) if hasattr(item, "get") else 0
                try:
                    values.append(float(raw))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Valor de gráfico inválido: {raw!r}") from exc
            max_value = max([abs(v) for v in values] + [1.0])
            label_width = 155
            value_width = 55
            track_x = MARGIN + label_width
            track_width = CONTENT_WIDTH - label_width - value_width
            row_height = 52
            needed = row_height * len(batch) + BLOCK_GAP
            context.ensure_space(needed)
            top = context.y
            for index, (item, number) in enumerate(zip(batch, values)):
                row_top = top - index * row_height
                label = item_text(item, "label", "title", default="Indicador")
                note = item_text(item, "note", "description")
                label_p = context.paragraph(label, "compact")
                _, label_h = label_p.wrap(label_width - 12, 28)
                label_p.drawOn(context.canvas, MARGIN, row_top - 12 - label_h)
                if note:
                    note_p = context.paragraph(note, "meta")
                    _, note_h = note_p.wrap(label_width - 12, 22)
                    note_p.drawOn(context.canvas, MARGIN, row_top - 30 - note_h)
                bar_y = row_top - 27
                rounded_box(context.canvas, track_x, bar_y, track_width, 18, SOFT, radius=9)
                bar_width = max(3.0, abs(number) / max_value * track_width)
                rounded_box(
                    context.canvas, track_x, bar_y, bar_width, 18,
                    BLUE if index % 2 == 0 else BLUE_2, radius=9,
                )
                context.canvas.setFillColor(DARK)
                context.canvas.setFont(FONT_SEMIBOLD, 8)
                rendered_value = f"{number:g}{unit}"
                context.canvas.drawRightString(PAGE_WIDTH - MARGIN, bar_y + 6, rendered_value)
                context.record(
                    "chart-row", MARGIN, row_top - row_height + 4, CONTENT_WIDTH, row_height - 4,
                    component_type=self.type_name, label=label,
                )
            context.y = top - row_height * len(batch) - BLOCK_GAP


RENDERER = ChartRenderer()
