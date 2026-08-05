from __future__ import annotations

from collections.abc import Mapping

from reportlab.platypus import Table, TableStyle

from pdfy.design.colors import BLUE, LINE, SOFT, WHITE
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import BLOCK_GAP

from .base import ComponentRenderer, draw_component_title, items, value


class TableRenderer(ComponentRenderer):
    type_name = "table"

    def render(self, component, context) -> None:
        draw_component_title(component, context, self.type_name)
        columns = list(value(component, "columns", value(component, "headers", ())) or ())
        raw_rows = items(component, "rows")
        if not columns and raw_rows and isinstance(raw_rows[0], Mapping):
            columns = list(raw_rows[0].keys())
        if not columns:
            columns = ["Item", "Descrição"]

        rows = []
        for row in raw_rows:
            if isinstance(row, Mapping):
                rows.append([row.get(column, "") for column in columns])
            else:
                cells = list(row) if not isinstance(row, str) else [row]
                rows.append(cells[:len(columns)] + [""] * max(0, len(columns) - len(cells)))

        header_style = context.styles["white_compact"]
        body_style = context.styles["compact"]
        table_data = [
            [context.paragraph(column, "white_compact") for column in columns],
            *[[context.paragraph(cell, "compact") for cell in row] for row in rows],
        ]
        col_widths = [CONTENT_WIDTH / len(columns)] * len(columns)
        pending = self._table(table_data, col_widths)
        while pending is not None:
            parts = pending.split(CONTENT_WIDTH, context.available_height)
            if not parts:
                context.continuation()
                parts = pending.split(CONTENT_WIDTH, context.available_height)
                if not parts:
                    raise ValueError("Uma linha da tabela excede a altura útil da página.")
            page_table = parts[0]
            pending = parts[1] if len(parts) > 1 else None
            _, height = page_table.wrap(CONTENT_WIDTH, context.available_height)
            bottom = context.y - height
            page_table.drawOn(context.canvas, MARGIN, bottom)
            context.record(
                "table", MARGIN, bottom, CONTENT_WIDTH, height,
                component_type=self.type_name, label="Tabela",
            )
            context.y = bottom - BLOCK_GAP
            if pending is not None:
                context.continuation()

    @staticmethod
    def _table(data, widths):
        table = Table(data, colWidths=widths, repeatRows=1, splitByRow=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SOFT]),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ]))
        return table


RENDERER = TableRenderer()
