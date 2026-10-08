"""Internal page chrome: logo, hierarchy and footer."""

from __future__ import annotations

from pdfy.design.colors import BLUE, DARK, LINE, MID
from pdfy.design.dimensions import (
    CONTENT_WIDTH,
    FOOTER_LINE_Y,
    FOOTER_TEXT_Y,
    MARGIN,
    PAGE_HEIGHT,
    PAGE_WIDTH,
)
from pdfy.design.typography import FONT_REGULAR, FONT_SEMIBOLD

from .assets import image_asset
from .paginator import RenderContext, plain_text


def draw_section_header(
    context: RenderContext,
    title: str,
    subtitle: str = "",
    *,
    continued: bool,
) -> float:
    canvas = context.canvas
    logo = image_asset("logos", "logo-dark.png")
    logo_x, logo_y, logo_w, logo_h = MARGIN, PAGE_HEIGHT - 62, 102, 29.1
    canvas.drawImage(logo, logo_x, logo_y, logo_w, logo_h, preserveAspectRatio=True, mask="auto")
    context.record("logo", logo_x, logo_y, logo_w, logo_h, label="Matizze", zone="chrome")

    eyebrow = "SEÇÃO"
    if continued:
        eyebrow += "  •  CONTINUAÇÃO"
    canvas.setFillColor(BLUE)
    canvas.setFont(FONT_SEMIBOLD, 7.3)
    canvas.drawString(MARGIN, PAGE_HEIGHT - 96, eyebrow)
    context.record("eyebrow", MARGIN, PAGE_HEIGHT - 98, CONTENT_WIDTH, 10, label=eyebrow, zone="chrome")

    display_title = plain_text(title)
    title_p = context.paragraph(display_title, "page_title")
    _, title_h = title_p.wrap(CONTENT_WIDTH, 100)
    title_top = PAGE_HEIGHT - 110
    title_y = title_top - title_h
    title_p.drawOn(canvas, MARGIN, title_y)
    context.record("section-title", MARGIN, title_y, CONTENT_WIDTH, title_h, label=display_title, zone="chrome")

    line_y = title_y - 14
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.7)
    canvas.line(MARGIN, line_y, PAGE_WIDTH - MARGIN, line_y)
    context.record("divider", MARGIN, line_y, CONTENT_WIDTH, 0.7, zone="chrome")
    y = line_y - 18
    if subtitle and not continued:
        subtitle_p = context.paragraph(subtitle, "body")
        _, subtitle_h = subtitle_p.wrap(CONTENT_WIDTH, 80)
        subtitle_y = y - subtitle_h
        subtitle_p.drawOn(canvas, MARGIN, subtitle_y)
        context.record("section-subtitle", MARGIN, subtitle_y, CONTENT_WIDTH, subtitle_h, label=subtitle, zone="chrome")
        y = subtitle_y - 18
    return y


def draw_content_header(context: RenderContext) -> float:
    """Minimal chrome for prose pages: logo only, blank middle, ready for text."""

    canvas = context.canvas
    logo = image_asset("logos", "logo-dark.png")
    logo_x, logo_y, logo_w, logo_h = MARGIN, PAGE_HEIGHT - 62, 102, 29.1
    canvas.drawImage(logo, logo_x, logo_y, logo_w, logo_h, preserveAspectRatio=True, mask="auto")
    context.record("logo", logo_x, logo_y, logo_w, logo_h, label="Matizze", zone="chrome")
    return PAGE_HEIGHT - 98.0


def draw_footer(context: RenderContext) -> None:
    canvas = context.canvas
    page = context.current_page
    if page is None:
        return
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, FOOTER_LINE_Y, PAGE_WIDTH - MARGIN, FOOTER_LINE_Y)
    canvas.setFillColor(MID)
    canvas.setFont(FONT_REGULAR, 6.6)
    section = (page.section_title or "").upper()
    left = f"matizze.  •  {section}" if section else "matizze."
    canvas.drawString(MARGIN, FOOTER_TEXT_Y, left)
    canvas.drawRightString(PAGE_WIDTH - MARGIN, FOOTER_TEXT_Y, f"{page.number:02d}")
    context.record("footer", MARGIN, FOOTER_TEXT_Y - 2, CONTENT_WIDTH, 15, label=left, zone="chrome")
