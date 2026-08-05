from __future__ import annotations

import shutil
from pathlib import Path

import pdfplumber
import pytest
from pypdf import PdfReader

from pdfy.engine import generate_pdf
from pdfy.parser import parse_document
from pdfy.validation.pdf import (
    compare_with_golden,
    create_contact_sheet,
    inspect_pdf,
    render_pdf,
)


def _document() -> dict:
    return {
        "schema": "1",
        "title": "Relatório de execução determinística",
        "subtitle": "Texto vetorial, acentos e composição automática.",
        "recipient": "Equipe de qualidade",
        "date": "2026-08-05",
        "sections": [
            {
                "title": "Síntese operacional",
                "subtitle": "Uma seção deliberadamente curta",
                "components": [
                    {
                        "type": "text",
                        "title": "Mensagem",
                        "content": (
                            "Informação, execução, análise e decisão permanecem "
                            "selecionáveis no PDF final."
                        ),
                    }
                ],
            }
        ],
    }


def test_generation_adds_cover_section_and_fixed_closing(tmp_path: Path) -> None:
    document = parse_document(_document())
    result = generate_pdf(document, tmp_path / "document.pdf")

    assert result.path.is_file()
    assert [page.role for page in result.trace.pages] == ["cover", "section", "closing"]
    assert result.trace.section_start_pages == {0: 2}

    reader = PdfReader(str(result.path))
    assert len(reader.pages) == 3
    assert reader.metadata.title == document.title
    assert reader.metadata.author == "Matizze"
    cover_text = " ".join((reader.pages[0].extract_text() or "").split())
    assert document.title in cover_text
    closing_text = reader.pages[-1].extract_text() or ""
    assert "Tecnologia como meio, resultado como foco." in closing_text
    assert "DOCUMENTO CONFIDENCIAL" not in closing_text


def test_generation_is_byte_deterministic(tmp_path: Path) -> None:
    first = generate_pdf(_document(), tmp_path / "first.pdf")
    second = generate_pdf(_document(), tmp_path / "second.pdf")

    assert first.path.read_bytes() == second.path.read_bytes()


def test_pdf_audit_preserves_accents_fonts_metadata_and_geometry(tmp_path: Path) -> None:
    document = parse_document(_document())
    result = generate_pdf(document, tmp_path / "audited.pdf")

    report = inspect_pdf(result.path, document=document, layout_trace=result.trace)

    assert report["ok"], report["issues"]
    assert report["pages"] == 3
    assert report["section_start_pages"] == [2]
    assert all(page["a4"] and page["rotation"] == 0 for page in report["geometry"])
    assert any(
        "montserrat" in font["name"].casefold() and font["embedded"]
        for font in report["fonts"]
    )
    assert all(page["out_of_bounds_characters"] == 0 for page in report["page_stats"])
    assert all(page["out_of_bounds_objects"] == 0 for page in report["page_stats"])

    with pdfplumber.open(str(result.path)) as pdf:
        extracted = "\n".join(page.extract_text() or "" for page in pdf.pages)
    for word in ("Informação", "execução", "análise", "decisão"):
        assert word in extracted


def test_all_pages_render_and_visual_comparator_is_stable(tmp_path: Path) -> None:
    if shutil.which("pdftoppm") is None:
        pytest.skip("Poppler não está instalado neste ambiente.")
    result = generate_pdf(_document(), tmp_path / "rendered.pdf")
    render_dir = tmp_path / "render"

    pages = render_pdf(result.path, render_dir)
    sheet = create_contact_sheet(pages, render_dir / "contact-sheet.png")
    comparison = compare_with_golden(pages, render_dir)

    assert [path.name for path in pages] == [
        "page-001.png",
        "page-002.png",
        "page-003.png",
    ]
    assert sheet.is_file()
    assert comparison["ok"], comparison["issues"]
    assert comparison["thresholds"]["max_changed_fraction"] == 0.005
    assert all(page["mae"] == 0 for page in comparison["pages"])
