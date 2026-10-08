from __future__ import annotations

from pathlib import Path

import pdfplumber
import pytest

from pdfy.engine import generate_pdf
from pdfy.errors import PdfyValidationError
from pdfy.parser import load_document, parse_document
from pdfy.validation.layout import validate_layout_trace
from pdfy.validation.pdf import inspect_pdf

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _content_document(content: str) -> dict:
    return {
        "schema": "1",
        "title": "Relatório em Markdown",
        "recipient": "Equipe",
        "date": "2026-10-07",
        "content": content,
    }


def test_markdown_document_uses_content_pages_without_section_chrome(tmp_path: Path) -> None:
    document = parse_document(
        _content_document(
            "## Como começou\n\nUm parágrafo objetivo com acentuação.\n\n"
            "## O que foi feito\n\nOutro parágrafo de fechamento."
        )
    )
    result = generate_pdf(document, tmp_path / "markdown.pdf")

    roles = [page.role for page in result.trace.pages]
    assert roles[0] == "cover"
    assert roles[-1] == "closing"
    assert set(roles[1:-1]) == {"content"}
    assert "SEÇÃO" not in " ".join(
        item.label or "" for page in result.trace.pages for item in page.items
    )

    report = inspect_pdf(result.path, document=document, layout_trace=result.trace)
    assert report["ok"], report["issues"]
    assert report["section_start_pages"] == []

    layout = validate_layout_trace(result.trace, page_count=len(result.trace.pages))
    assert layout["ok"], layout["issues"]


def test_content_and_sections_are_mutually_exclusive() -> None:
    both = _content_document("## Título")
    both["sections"] = [{"title": "Resumo", "components": [{"type": "text", "content": "Texto."}]}]
    with pytest.raises(PdfyValidationError) as conflict:
        parse_document(both)
    assert any(issue.code == "content_mode_conflict" for issue in conflict.value.issues)

    with pytest.raises(PdfyValidationError) as missing:
        parse_document({"schema": "1", "title": "Sem corpo"})
    assert any(issue.code == "content_mode_missing" for issue in missing.value.issues)


def test_empty_markdown_is_rejected() -> None:
    with pytest.raises(PdfyValidationError) as caught:
        parse_document(_content_document("   \n  "))
    assert any(issue.code == "too_short" for issue in caught.value.issues)


def test_markdown_features_survive_rendering(tmp_path: Path) -> None:
    content = (
        "# Título principal\n\n"
        "Texto com **negrito**, *ênfase* e `código`.\n\n"
        "- Primeiro item com marcador.\n"
        "- Segundo item com marcador.\n"
        "  1. Subitem numerado.\n\n"
        "> Uma citação de destaque.\n\n"
        "| Camada | Saída |\n|---|---|\n| Conteúdo | JSON |\n| Renderer | PDF |\n\n"
        "```\ncodigo = True\n```\n"
    )
    result = generate_pdf(_content_document(content), tmp_path / "features.pdf")

    with pdfplumber.open(str(result.path)) as pdf:
        extracted = "\n".join(page.extract_text() or "" for page in pdf.pages)
    for sentinel in (
        "Título principal",
        "negrito",
        "Primeiro item com marcador",
        "Subitem numerado",
        "Uma citação de destaque",
        "Renderer",
        "codigo = True",
    ):
        assert sentinel in extracted


def test_markdown_example_is_valid_and_deterministic(tmp_path: Path) -> None:
    source = PROJECT_ROOT / "examples" / "markdown-document.json"
    document = load_document(source)

    first = generate_pdf(document, tmp_path / "first.pdf")
    second = generate_pdf(document, tmp_path / "second.pdf")

    assert first.path.read_bytes() == second.path.read_bytes()
    assert first.trace.pages[0].role == "cover"
    assert first.trace.pages[-1].role == "closing"
    assert all(page.role == "content" for page in first.trace.pages[1:-1])

    report = inspect_pdf(first.path, document=document, layout_trace=first.trace)
    assert report["ok"], report["issues"]
