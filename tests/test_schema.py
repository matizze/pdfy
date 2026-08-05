from __future__ import annotations

import json
import unicodedata

import pytest

from pdfy.errors import PdfyValidationError
from pdfy.parser import load_document, parse_document
from pdfy.validation.content import COMPONENT_TYPES, load_schema


def minimal_document(component: dict | None = None) -> dict:
    return {
        "schema": "1",
        "title": "Documento mínimo",
        "sections": [
            {
                "title": "Resumo",
                "components": [component or {"type": "text", "content": "Conteúdo."}],
            }
        ],
    }


def test_schema_is_valid_draft_2020_12() -> None:
    schema = load_schema()
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["properties"]["schema"]["const"] == "1"


def test_minimal_document_is_normalized_and_immutable() -> None:
    decomposed = "Ac\u0327a\u0303o\r\nseguinte"
    document = parse_document(minimal_document({"type": "text", "content": decomposed}))

    assert document.schema == "1"
    assert document.sections[0].components[0]["content"] == "Ação\nseguinte"
    assert unicodedata.is_normalized("NFC", document.sections[0].components[0]["content"])
    with pytest.raises(TypeError):
        document.sections[0].components[0].data["content"] = "alterado"


@pytest.mark.parametrize(
    ("component_type", "component"),
    [
        ("text", {"type": "text", "content": "Texto."}),
        ("metrics", {"type": "metrics", "items": [{"label": "Prazo", "value": "30 dias"}]}),
        ("highlights", {"type": "highlights", "items": ["Objetivo claro."]}),
        ("cards", {"type": "cards", "items": [{"title": "Entrega", "description": "Descrição."}]}),
        ("callout", {"type": "callout", "content": "Decisão principal."}),
        (
            "comparison",
            {
                "type": "comparison",
                "left_label": "Atual",
                "right_label": "Futuro",
                "rows": [{"label": "Processo", "left": "Manual", "right": "Padronizado"}],
            },
        ),
        ("chart", {"type": "chart", "unit": "%", "items": [{"label": "Conversão", "value": 35}]}),
        ("steps", {"type": "steps", "items": [{"title": "Validar", "description": "Aprovar."}]}),
        ("timeline", {"type": "timeline", "items": [{"period": "Semana 1", "title": "Preparação"}]}),
        ("table", {"type": "table", "columns": ["Item", "Valor"], "rows": [["Serviço", "R$ 0,00"]]}),
        ("investment", {"type": "investment", "items": [{"label": "Implantação", "value": "R$ 0,00"}]}),
        ("list", {"type": "list", "items": ["Primeiro item."]}),
        ("signature", {"type": "signature", "signers": [{"name": "[PREENCHER]"}]}),
    ],
)
def test_every_component_has_a_valid_minimal_shape(component_type: str, component: dict) -> None:
    assert component_type in COMPONENT_TYPES
    parsed = parse_document(minimal_document(component))
    assert parsed.sections[0].components[0].type == component_type


def test_complete_document_accepts_only_content_fields() -> None:
    data = minimal_document()
    data.update(
        {
            "subtitle": "Subtítulo",
            "recipient": "Destinatário",
            "date": "2026-08-05",
        }
    )
    data["sections"][0]["subtitle"] = "Uma visão objetiva"
    document = parse_document(data)
    assert document.date == "2026-08-05"
    assert document.recipient == "Destinatário"


def test_unknown_component_has_one_actionable_error() -> None:
    with pytest.raises(PdfyValidationError) as caught:
        parse_document(minimal_document({"type": "quote", "content": "Não existe."}))

    assert len(caught.value.issues) == 1
    issue = caught.value.issues[0]
    assert issue.path == "$.sections[0].components[0].type"
    assert issue.code == "unknown_component"
    assert "Permitidos:" in (issue.hint or "")


def test_visual_property_is_rejected_with_explanation() -> None:
    component = {"type": "text", "content": "Texto", "color": "#000000"}
    with pytest.raises(PdfyValidationError) as caught:
        parse_document(minimal_document(component))

    issue = next(item for item in caught.value.issues if item.code == "unexpected_property")
    assert issue.path.endswith(".color")
    assert "controlada pelo pdfy" in (issue.hint or "")


def test_invalid_calendar_date_is_rejected() -> None:
    data = minimal_document()
    data["date"] = "2026-02-30"
    with pytest.raises(PdfyValidationError) as caught:
        parse_document(data)
    assert any(issue.code == "invalid_date" for issue in caught.value.issues)


def test_table_row_must_match_column_count() -> None:
    component = {"type": "table", "columns": ["Item", "Prazo", "Valor"], "rows": [["Serviço", "30 dias"]]}
    with pytest.raises(PdfyValidationError) as caught:
        parse_document(minimal_document(component))
    assert any(issue.code == "table_width" for issue in caught.value.issues)


def test_duplicate_json_keys_are_rejected() -> None:
    raw = '{"schema":"1","title":"Um","title":"Dois","sections":[]}'
    with pytest.raises(PdfyValidationError) as caught:
        load_document(raw)
    assert caught.value.issues[0].code == "duplicate_key"


def test_non_finite_numbers_are_rejected_from_json_and_mapping() -> None:
    raw = '{"schema":"1","title":"Teste","sections":[],"value":NaN}'
    with pytest.raises(PdfyValidationError) as caught_json:
        load_document(raw)
    assert caught_json.value.issues[0].code == "non_finite_number"

    data = minimal_document({"type": "chart", "items": [{"label": "A", "value": float("inf")} ]})
    with pytest.raises(PdfyValidationError) as caught_mapping:
        parse_document(data)
    assert any(issue.code == "non_finite_number" for issue in caught_mapping.value.issues)


def test_multiple_errors_are_reported_together() -> None:
    data = {"schema": "2", "title": "", "sections": []}
    with pytest.raises(PdfyValidationError) as caught:
        parse_document(data)
    codes = {issue.code for issue in caught.value.issues}
    assert {"const", "too_short", "too_few_items"}.issubset(codes)


def test_loads_utf8_file(tmp_path) -> None:
    path = tmp_path / "documento.json"
    path.write_text(json.dumps(minimal_document(), ensure_ascii=False), encoding="utf-8")
    assert load_document(path).title == "Documento mínimo"
