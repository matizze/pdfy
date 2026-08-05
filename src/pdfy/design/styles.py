"""Small drawing helpers; no component owns brand styling."""

from __future__ import annotations

from reportlab.pdfgen.canvas import Canvas

from .colors import LINE


def rounded_box(
    canvas: Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    fill,
    *,
    radius: float = 10,
    stroke=None,
) -> None:
    canvas.setFillColor(fill)
    canvas.setStrokeColor(stroke or fill)
    canvas.roundRect(x, y, width, height, radius, fill=1, stroke=1 if stroke else 0)


def divider(canvas: Canvas, x1: float, y: float, x2: float, *, width: float = 0.5) -> None:
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(width)
    canvas.line(x1, y, x2, y)
