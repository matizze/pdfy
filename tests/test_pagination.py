from __future__ import annotations

from pathlib import Path

import pdfplumber

from pdfy.engine import generate_pdf
from pdfy.parser import load_document
from pdfy.validation.layout import validate_layout_trace
from pdfy.validation.pdf import inspect_pdf


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _two_short_sections() -> dict:
    return {
        "schema": "1",
        "title": "Seções independentes",
        "sections": [
            {
                "title": "Primeira seção",
                "components": [{"type": "text", "content": "Conteúdo curto da primeira seção."}],
            },
            {
                "title": "Segunda seção",
                "components": [{"type": "text", "content": "Conteúdo curto da segunda seção."}],
            },
        ],
    }


def test_each_section_starts_on_a_fresh_page(tmp_path: Path) -> None:
    result = generate_pdf(_two_short_sections(), tmp_path / "sections.pdf")

    assert [page.role for page in result.trace.pages] == [
        "cover",
        "section",
        "section",
        "closing",
    ]
    assert result.trace.section_start_pages == {0: 2, 1: 3}
    with pdfplumber.open(str(result.path)) as pdf:
        assert "Primeira seção" in (pdf.pages[1].extract_text() or "")
        assert "Segunda seção" in (pdf.pages[2].extract_text() or "")


def test_long_section_continues_without_overflow_or_content_loss(tmp_path: Path) -> None:
    source = PROJECT_ROOT / "examples" / "long-document.json"
    document = load_document(source)
    result = generate_pdf(document, tmp_path / "long.pdf")

    continuation_pages = [page for page in result.trace.pages if page.role == "continuation"]
    assert len(continuation_pages) >= 2
    assert result.trace.section_start_pages[0] == 2
    assert result.trace.section_start_pages[1] > continuation_pages[-1].number
    assert result.trace.pages[-1].role == "closing"

    layout_report = validate_layout_trace(
        result.trace,
        page_count=len(result.trace.pages),
        expected_sections=2,
    )
    assert layout_report["ok"], layout_report["issues"]
    assert layout_report["items_checked"] > 0

    report = inspect_pdf(result.path, document=document, layout_trace=result.trace)
    assert report["ok"], report["issues"]
    assert all(page["out_of_bounds_characters"] == 0 for page in report["page_stats"])
    assert all(page["out_of_bounds_objects"] == 0 for page in report["page_stats"])

    with pdfplumber.open(str(result.path)) as pdf:
        extracted = "\n".join(page.extract_text() or "" for page in pdf.pages)
    for sentinel in (
        "PAGINACAO-TEXTO-CONCLUIDA",
        "PAGINACAO-LISTA-CONCLUIDA",
        "PAGINACAO-TABELA-CONCLUIDA",
        "SECAO-DOIS-INICIO-PROPRIO",
    ):
        assert sentinel in extracted
