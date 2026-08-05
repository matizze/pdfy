"""A4 geometry shared by templates and components."""

from reportlab.lib.pagesizes import A4


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 46.0
COVER_MARGIN = 56.0
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
TOP_CONTENT = PAGE_HEIGHT - 142.0
BOTTOM_SAFE = 55.0
FOOTER_LINE_Y = 38.0
FOOTER_TEXT_Y = 25.0
