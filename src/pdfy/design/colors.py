"""Canonical Matizze colour tokens."""

from reportlab.lib import colors


BLUE = colors.HexColor("#0033FF")
BLUE_2 = colors.HexColor("#3366FF")
DARK = colors.HexColor("#16161C")
INK = colors.HexColor("#22212F")
MINT = colors.HexColor("#9AF3D4")
SKY = colors.HexColor("#9CD3F9")
PAPER = colors.HexColor("#FAFAFA")
WHITE = colors.white
SOFT = colors.HexColor("#F2F4F8")
LINE = colors.HexColor("#DFE3EC")
MID = colors.HexColor("#626775")

BLUE_SURFACE = colors.HexColor("#EAF0FF")
MINT_SURFACE = colors.HexColor("#E6FFF6")
SKY_SURFACE = colors.HexColor("#EAF7FF")

TONES = {
    "blue": (BLUE_SURFACE, BLUE),
    "mint": (MINT_SURFACE, DARK),
    "sky": (SKY_SURFACE, DARK),
    "dark": (DARK, WHITE),
    "soft": (SOFT, INK),
}
