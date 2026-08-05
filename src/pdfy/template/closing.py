"""Mandatory immutable closing page approved by Matizze."""

from reportlab.lib import colors

from pdfy.design.colors import MINT
from pdfy.design.dimensions import PAGE_HEIGHT, PAGE_WIDTH
from pdfy.design.typography import FONT_SEMIBOLD

from .assets import image_asset
from .cover import _draw_cover_image
from .paginator import RenderContext


CLOSING_HEADLINE = "Tecnologia como meio, resultado como foco."
CLOSING_URL = "www.matizze.com.br"


def draw_closing(context: RenderContext) -> None:
    context.finish_page()
    context.open_page("closing")
    canvas = context.canvas
    _draw_cover_image(context, "gradient-dark.png")
    canvas.setFillColor(colors.Color(0, 0, 0, alpha=0.16))
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    canvas.setFillAlpha(1)

    logo = image_asset("logos", "logo-white.png")
    logo_x, logo_y = PAGE_WIDTH / 2 - 75, PAGE_HEIGHT / 2 + 26
    canvas.drawImage(logo, logo_x, logo_y, 150, 43, preserveAspectRatio=True, mask="auto")
    context.record("logo", logo_x, logo_y, 150, 43, label="Matizze", zone="closing")

    headline = context.paragraph(CLOSING_HEADLINE, "centered_white")
    headline_width = PAGE_WIDTH - 220
    _, headline_h = headline.wrap(headline_width, 60)
    headline_y = PAGE_HEIGHT / 2 - 5 - headline_h
    headline.drawOn(canvas, 110, headline_y)
    context.record("closing-headline", 110, headline_y, headline_width, headline_h, label=CLOSING_HEADLINE, zone="closing")

    canvas.setFillColor(MINT)
    canvas.setFont(FONT_SEMIBOLD, 7.2)
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT / 2 - 38, CLOSING_URL)
    context.record("closing-url", 110, PAGE_HEIGHT / 2 - 40, PAGE_WIDTH - 220, 10, label=CLOSING_URL, zone="closing")

    context.finish_page(footer=False)
