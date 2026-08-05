"""Automatic cover for the official Matizze template."""

from __future__ import annotations

from collections.abc import Mapping

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from pdfy.design.colors import MINT, WHITE
from pdfy.design.dimensions import COVER_MARGIN, PAGE_HEIGHT, PAGE_WIDTH
from pdfy.design.styles import rounded_box
from pdfy.design.typography import FONT_BOLD, FONT_REGULAR, FONT_SEMIBOLD

from .assets import image_asset
from .paginator import RenderContext, plain_text, safe_text


def _value(obj, name: str, default=None):
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _cover_metrics(document) -> list[Mapping]:
    """Reuse content facts without adding cover-specific visual controls."""
    for section in _value(document, "sections", ()) or ():
        for component in _value(section, "components", ()) or ():
            if plain_text(_value(component, "type", "")).lower() != "metrics":
                continue
            items = _value(component, "items", ()) or ()
            usable = [
                item for item in items
                if isinstance(item, Mapping)
                and len(plain_text(item.get("label", ""))) <= 24
                and len(plain_text(item.get("value", ""))) <= 28
            ]
            return usable[:3]
    return []


def _draw_cover_image(context: RenderContext, name: str) -> None:
    image = image_asset("backgrounds", name)
    iw, ih = image.getSize()
    scale = max(PAGE_WIDTH / iw, PAGE_HEIGHT / ih)
    width, height = iw * scale, ih * scale
    x, y = (PAGE_WIDTH - width) / 2, (PAGE_HEIGHT - height) / 2
    context.canvas.drawImage(image, x, y, width, height, preserveAspectRatio=True, mask="auto")
    context.record("background", 0, 0, PAGE_WIDTH, PAGE_HEIGHT, label=name, zone="background")


def draw_cover(context: RenderContext, document) -> None:
    context.open_page("cover")
    canvas = context.canvas
    _draw_cover_image(context, "gradient-dark.png")
    canvas.setFillColor(colors.Color(0, 0, 0, alpha=0.12))
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    canvas.setFillAlpha(1)

    logo = image_asset("logos", "logo-white.png")
    canvas.drawImage(logo, COVER_MARGIN, PAGE_HEIGHT - 83, 102, 29.1, preserveAspectRatio=True, mask="auto")
    context.record("logo", COVER_MARGIN, PAGE_HEIGHT - 83, 102, 29.1, label="Matizze", zone="cover")

    canvas.setFillColor(MINT)
    canvas.setFont(FONT_SEMIBOLD, 8.4)
    eyebrow = "DOCUMENTO MATIZZE"
    canvas.drawString(COVER_MARGIN, 568, eyebrow)
    context.record("eyebrow", COVER_MARGIN, 566, 455, 12, label=eyebrow, zone="cover")

    title = plain_text(_value(document, "title", "Documento Matizze"))
    title_size = 27 if len(title) <= 72 else 23.5
    title_style = ParagraphStyle(
        "PdfyCoverTitle", fontName=FONT_BOLD, fontSize=title_size,
        leading=title_size * 1.18, textColor=WHITE,
    )
    title_p = Paragraph(safe_text(title), title_style)
    _, title_h = title_p.wrap(455, 180)
    title_y = 547 - title_h
    title_p.drawOn(canvas, COVER_MARGIN, title_y)
    context.record("cover-title", COVER_MARGIN, title_y, 455, title_h, label=title, zone="cover")

    subtitle = plain_text(_value(document, "subtitle", ""))
    content_bottom = title_y
    if subtitle:
        subtitle_style = ParagraphStyle(
            "PdfyCoverSubtitle", fontName=FONT_REGULAR, fontSize=9.1,
            leading=13, textColor=WHITE,
        )
        subtitle_p = Paragraph(safe_text(subtitle), subtitle_style)
        _, subtitle_h = subtitle_p.wrap(405, 120)
        subtitle_y = title_y - 17 - subtitle_h
        subtitle_p.drawOn(canvas, COVER_MARGIN, subtitle_y)
        context.record("cover-subtitle", COVER_MARGIN, subtitle_y, 405, subtitle_h, label=subtitle, zone="cover")
        content_bottom = subtitle_y

    metrics = _cover_metrics(document)
    if metrics:
        gap = 9.0
        total_w = 405.0
        pill_w = (total_w - gap * (len(metrics) - 1)) / len(metrics)
        for index, metric in enumerate(metrics):
            x = COVER_MARGIN + index * (pill_w + gap)
            tone = "mint" if index == len(metrics) - 1 else "blue"
            fill = colors.HexColor("#E6FFF6") if tone == "mint" else colors.HexColor("#EAF0FF")
            text_color = colors.HexColor("#16161C") if tone == "mint" else colors.HexColor("#0033FF")
            rounded_box(canvas, x, 304, pill_w, 30, fill, radius=15)
            label = plain_text(metric.get("label", "DESTAQUE")).upper()
            value = plain_text(metric.get("value", metric.get("content", "")))
            canvas.setFillColor(text_color)
            canvas.setFont(FONT_SEMIBOLD, 7.0)
            canvas.drawString(x + 13, 321.5, label)
            canvas.setFont(FONT_BOLD, 8)
            canvas.drawString(x + 13, 311, value)
            context.record("cover-metric", x, 304, pill_w, 30, component_type="metrics", label=label, zone="cover")

    meta = "  •  ".join(
        part for part in (
            plain_text(_value(document, "recipient", "")),
            plain_text(_value(document, "date", "")),
        ) if part
    )
    if meta:
        canvas.setFillColor(colors.Color(1, 1, 1, alpha=0.66))
        canvas.setFont(FONT_REGULAR, 7.3)
        canvas.drawString(COVER_MARGIN, 276, meta)
        context.record("cover-meta", COVER_MARGIN, 274, 455, 11, label=meta, zone="cover")

    mark = image_asset("logos", "mark-white.png")
    canvas.drawImage(mark, COVER_MARGIN, 58, 30, 30, preserveAspectRatio=True, mask="auto")
    context.record("mark", COVER_MARGIN, 58, 30, 30, label="Matizze", zone="cover")
    context.finish_page(footer=False)
