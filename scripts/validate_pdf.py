#!/usr/bin/env python3
"""Validate, render and optionally compare one pdfy document with a golden."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pdfy.errors import PdfyValidationError
from pdfy.parser import load_document
from pdfy.validation.pdf import (
    DEFAULT_RENDER_DPI,
    PdfValidationDependencyError,
    compare_with_golden,
    create_contact_sheet,
    inspect_pdf,
    pdfium_version,
    render_pdf,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida tecnicamente e renderiza um PDF gerado pelo pdfy."
    )
    parser.add_argument("--pdf", required=True, type=Path, help="PDF a validar")
    parser.add_argument("--input", type=Path, help="JSON original para validação cruzada")
    parser.add_argument(
        "--render-dir", required=True, type=Path, help="Diretório para PNGs e contact sheet"
    )
    parser.add_argument("--layout-trace", type=Path, help="Trace JSON opcional do renderer")
    parser.add_argument("--golden", type=Path, help="Diretório de PNGs golden")
    parser.add_argument("--report", type=Path, help="Destino do relatório JSON")
    parser.add_argument("--dpi", type=int, default=DEFAULT_RENDER_DPI)
    return parser


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"arquivo não encontrado: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"não foi possível ler JSON '{path}': {exc}") from exc


def _emit(report: dict[str, Any], report_path: Path | None) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.dpi < 72 or args.dpi > 600:
        _emit(
            {
                "ok": False,
                "stage": "arguments",
                "issues": ["--dpi deve estar entre 72 e 600."],
                "warnings": [],
            },
            args.report,
        )
        return 2

    try:
        document = load_document(args.input) if args.input else None
        trace_path = args.layout_trace
        if trace_path is None:
            candidates = (
                args.pdf.with_suffix(".layout.json"),
                Path(str(args.pdf) + ".layout.json"),
            )
            trace_path = next((candidate for candidate in candidates if candidate.is_file()), None)
        trace = _read_json(trace_path) if trace_path else None
    except PdfyValidationError as exc:
        _emit(
            {
                "ok": False,
                "stage": "input",
                "issues": [
                    {
                        "path": issue.path,
                        "code": issue.code,
                        "message": issue.message,
                        "hint": issue.hint,
                    }
                    for issue in exc.issues
                ],
                "warnings": [],
            },
            args.report,
        )
        return 2
    except ValueError as exc:
        _emit(
            {"ok": False, "stage": "input", "issues": [str(exc)], "warnings": []},
            args.report,
        )
        return 2

    try:
        technical = inspect_pdf(args.pdf, document=document, layout_trace=trace)
        pages = render_pdf(args.pdf, args.render_dir, dpi=args.dpi)
        sheet = create_contact_sheet(pages, args.render_dir / "contact-sheet.png")
        render_report: dict[str, Any] = {
            "ok": len(pages) == technical.get("pages"),
            "dpi": args.dpi,
            "renderer": pdfium_version(),
            "pages": [str(path.resolve()) for path in pages],
            "contact_sheet": str(sheet.resolve()),
            "issues": [],
        }
        if not render_report["ok"]:
            render_report["issues"].append(
                f"Foram renderizadas {len(pages)} páginas, mas o PDF registra "
                f"{technical.get('pages', 0)}."
            )
        golden = (
            compare_with_golden(pages, args.golden)
            if args.golden is not None
            else {"ok": True, "skipped": True, "issues": []}
        )
        report = {
            "ok": bool(technical.get("ok")) and render_report["ok"] and golden["ok"],
            "stage": "complete",
            "technical": technical,
            "render": render_report,
            "golden": golden,
        }
        _emit(report, args.report)
        return 0 if report["ok"] else 1
    except PdfValidationDependencyError as exc:
        _emit(
            {"ok": False, "stage": "dependency", "issues": [str(exc)], "warnings": []},
            args.report,
        )
        return 3
    except (OSError, RuntimeError, ValueError) as exc:
        _emit(
            {"ok": False, "stage": "validation", "issues": [str(exc)], "warnings": []},
            args.report,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
