"""Embedded Montserrat registration and deterministic paragraph styles."""

from __future__ import annotations

from importlib import resources
from io import BytesIO

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .colors import BLUE, DARK, INK, MID, WHITE


FONT_REGULAR = "PdfyMontserrat"
FONT_MEDIUM = "PdfyMontserrat-Medium"
FONT_SEMIBOLD = "PdfyMontserrat-SemiBold"
FONT_BOLD = "PdfyMontserrat-Bold"

_FONT_FILES = {
    FONT_REGULAR: "Montserrat-Regular.ttf",
    FONT_MEDIUM: "Montserrat-Medium.ttf",
    FONT_SEMIBOLD: "Montserrat-SemiBold.ttf",
    FONT_BOLD: "Montserrat-Bold.ttf",
}


def asset_bytes(*parts: str) -> bytes:
    resource = resources.files("pdfy")
    for part in ("assets", *parts):
        resource = resource.joinpath(part)
    try:
        return resource.read_bytes()
    except FileNotFoundError as exc:
        path = "/".join(("pdfy", "assets", *parts))
        raise FileNotFoundError(f"Ativo obrigatório ausente no pacote: {path}") from exc


def register_fonts() -> None:
    registered = set(pdfmetrics.getRegisteredFontNames())
    for name, filename in _FONT_FILES.items():
        if name not in registered:
            pdfmetrics.registerFont(TTFont(name, BytesIO(asset_bytes("fonts", filename))))


def paragraph_styles() -> dict[str, ParagraphStyle]:
    register_fonts()
    body = ParagraphStyle(
        "PdfyBody", fontName=FONT_REGULAR, fontSize=9.2, leading=13.2,
        textColor=INK, spaceAfter=0,
    )
    compact = ParagraphStyle(
        "PdfyCompact", parent=body, fontSize=8.35, leading=11.7,
    )
    return {
        "body": body,
        "compact": compact,
        "meta": ParagraphStyle("PdfyMeta", parent=body, fontSize=8, leading=11.2, textColor=MID),
        "label": ParagraphStyle(
            "PdfyLabel", fontName=FONT_SEMIBOLD, fontSize=7.2, leading=9,
            textColor=BLUE,
        ),
        "page_title": ParagraphStyle(
            "PdfyPageTitle", fontName=FONT_BOLD, fontSize=21, leading=25,
            textColor=DARK,
        ),
        "h2": ParagraphStyle(
            "PdfyH2", fontName=FONT_SEMIBOLD, fontSize=11.4, leading=14,
            textColor=DARK,
        ),
        "white_body": ParagraphStyle(
            "PdfyWhiteBody", parent=body, fontSize=9.1, leading=13, textColor=WHITE,
        ),
        "white_compact": ParagraphStyle(
            "PdfyWhiteCompact", parent=compact, textColor=WHITE,
        ),
        "centered_white": ParagraphStyle(
            "PdfyCenteredWhite", fontName=FONT_REGULAR, fontSize=9, leading=13,
            textColor=WHITE, alignment=TA_CENTER,
        ),
    }
