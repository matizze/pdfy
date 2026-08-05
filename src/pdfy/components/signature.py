from __future__ import annotations

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from pdfy.design.colors import BLUE, DARK, MID, SOFT
from pdfy.design.dimensions import CONTENT_WIDTH, MARGIN
from pdfy.design.spacing import BLOCK_GAP, CARD_GAP
from pdfy.design.styles import rounded_box
from pdfy.template.paginator import safe_text

from .base import ComponentRenderer, draw_component_title, item_text, items, value


class SignatureRenderer(ComponentRenderer):
    type_name = "signature"

    def render(self, component, context) -> None:
        draw_component_title(component, context, self.type_name)
        intro = value(component, "intro", "")
        if intro:
            context.draw_paragraph_flow(
                intro, component_type=self.type_name, kind="signature-intro", gap_after=18,
            )
        entries = items(component, "signers") or items(component, "signatories") or items(component)
        width = (CONTENT_WIDTH - CARD_GAP) / 2
        for start in range(0, len(entries), 2):
            row = entries[start:start + 2]
            height = 140
            context.ensure_space(height)
            top = context.y
            for col, item in enumerate(row):
                x = MARGIN + col * (width + CARD_GAP)
                bottom = top - height
                rounded_box(context.canvas, x, bottom, width, height, SOFT, radius=10)
                context.canvas.setStrokeColor(MID)
                context.canvas.setLineWidth(0.6)
                context.canvas.line(x + 20, top - 73, x + width - 20, top - 73)
                name = item_text(item, "name", "title", default="[PREENCHER]")
                role = item_text(item, "role", "label", default="SIGNATÁRIO")
                organization = item_text(item, "organization")
                if organization:
                    role = f"{role} - {organization}" if role else organization
                document = item_text(item, "document", "identifier")
                name_p = Paragraph(
                    safe_text(name),
                    ParagraphStyle("SignatureName", parent=context.styles["h2"], alignment=TA_CENTER),
                )
                _, name_h = name_p.wrap(width - 40, 40)
                name_p.drawOn(context.canvas, x + 20, top - 94 - name_h)
                role_p = Paragraph(
                    safe_text(role.upper()),
                    ParagraphStyle("SignatureRole", parent=context.styles["label"], alignment=TA_CENTER),
                )
                _, role_h = role_p.wrap(width - 40, 30)
                role_p.drawOn(context.canvas, x + 20, top - 112 - role_h)
                if document:
                    doc_p = Paragraph(
                        safe_text(document),
                        ParagraphStyle("SignatureDocument", parent=context.styles["meta"], alignment=TA_CENTER),
                    )
                    _, doc_h = doc_p.wrap(width - 40, 25)
                    doc_p.drawOn(context.canvas, x + 20, bottom + 10)
                context.record(
                    "signature", x, bottom, width, height,
                    component_type=self.type_name, label=name,
                )
            context.y = top - height - BLOCK_GAP


RENDERER = SignatureRenderer()
