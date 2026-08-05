from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from pdfy.engine import generate_pdf
from pdfy.parser import parse_document
from pdfy.registry import supported_component_types
from pdfy.template.closing import CLOSING_HEADLINE, CLOSING_URL
from pdfy.validation.layout import validate_layout_trace


EXPECTED_COMPONENTS = {
    "text",
    "metrics",
    "highlights",
    "cards",
    "callout",
    "comparison",
    "chart",
    "steps",
    "timeline",
    "table",
    "investment",
    "list",
    "signature",
}


def minimal_document(content: str = "Conteúdo com acentuação em português.") -> dict:
    return {
        "schema": "1",
        "title": "Documento determinístico",
        "subtitle": "Composição automática",
        "recipient": "Equipe Matizze",
        "date": "2026-08-05",
        "sections": [
            {
                "title": "Resumo executivo",
                "subtitle": "Uma seção começa sempre em página nova",
                "components": [{"type": "text", "content": content}],
            }
        ],
    }


def test_registry_contains_exactly_the_public_components() -> None:
    assert set(supported_component_types()) == EXPECTED_COMPONENTS
    assert len(supported_component_types()) == 13


def test_complete_example_renders_every_component_and_a_valid_trace(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "complete-document.json"
    result = generate_pdf(example, tmp_path / "complete.pdf")

    assert result.path.is_file()
    assert result.trace.pages[0].role == "cover"
    assert result.trace.pages[-1].role == "closing"
    assert len(result.trace.section_start_pages) == 5
    rendered_types = {
        item.component_type
        for page in result.trace.pages
        for item in page.items
        if item.component_type
    }
    assert rendered_types == EXPECTED_COMPONENTS
    report = validate_layout_trace(
        result.trace,
        page_count=len(PdfReader(result.path).pages),
        expected_sections=5,
    )
    assert report["ok"], report["issues"]


def test_cover_closing_and_metadata_are_automatic(tmp_path: Path) -> None:
    result = generate_pdf(minimal_document(), tmp_path / "automatic.pdf")
    reader = PdfReader(result.path)
    summary = result.as_dict()

    assert len(reader.pages) == 3
    assert summary["path"] == str(result.path)
    assert summary["pages"] == 3
    assert summary["bytes"] == result.path.stat().st_size
    assert summary["trace"]["pages"][0]["role"] == "cover"
    assert reader.metadata.title == "Documento determinístico"
    assert "Documento determinístico" in (reader.pages[0].extract_text() or "")
    closing = reader.pages[-1].extract_text() or ""
    assert CLOSING_HEADLINE in closing
    assert CLOSING_URL in closing
    assert "DOCUMENTO CONFIDENCIAL" not in closing


def test_generation_is_byte_deterministic(tmp_path: Path) -> None:
    document = parse_document(minimal_document())
    first = generate_pdf(document, tmp_path / "first.pdf")
    second = generate_pdf(document, tmp_path / "second.pdf")
    assert first.path.read_bytes() == second.path.read_bytes()


def test_long_text_creates_safe_continuation_pages(tmp_path: Path) -> None:
    long_text = " ".join(
        f"Parágrafo {index} com informações financeiras, decisões e próximos passos."
        for index in range(180)
    )
    result = generate_pdf(minimal_document(long_text), tmp_path / "long.pdf")

    roles = [page.role for page in result.trace.pages]
    assert roles[0] == "cover"
    assert roles[1] == "section"
    assert "continuation" in roles
    assert roles[-1] == "closing"
    assert result.trace.section_start_pages == {0: 2}
    report = validate_layout_trace(
        result.trace,
        page_count=len(PdfReader(result.path).pages),
        expected_sections=1,
    )
    assert report["ok"], report["issues"]


def test_layout_validation_rejects_overlapping_content_blocks() -> None:
    trace = {
        "pages": [
            {
                "number": 1,
                "role": "cover",
                "safe_area": {"x": 46, "y": 55, "width": 503, "height": 740},
                "items": [],
            },
            {
                "number": 2,
                "role": "section",
                "safe_area": {"x": 46, "y": 55, "width": 503, "height": 740},
                "items": [
                    {
                        "kind": "card",
                        "zone": "content",
                        "bbox": {"x": 46, "y": 400, "width": 200, "height": 100},
                    },
                    {
                        "kind": "callout",
                        "zone": "content",
                        "bbox": {"x": 100, "y": 450, "width": 250, "height": 90},
                    },
                ],
            },
            {
                "number": 3,
                "role": "closing",
                "safe_area": {"x": 46, "y": 55, "width": 503, "height": 740},
                "items": [],
            },
        ]
    }

    report = validate_layout_trace(trace, page_count=3, expected_sections=1)

    assert not report["ok"]
    assert any("se sobrepõem" in issue for issue in report["issues"])
