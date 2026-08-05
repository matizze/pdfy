"""Deterministic, atomic PDF generation entry point."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reportlab.pdfgen import canvas

from pdfy.design.dimensions import PAGE_HEIGHT, PAGE_WIDTH
from pdfy.design.typography import paragraph_styles
from pdfy.template.document import DocumentRenderer, value
from pdfy.template.paginator import LayoutTrace


@dataclass(frozen=True)
class GenerationResult:
    path: Path
    trace: LayoutTrace

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "pages": len(self.trace.pages),
            "bytes": self.path.stat().st_size,
            "trace": self.trace.to_dict(),
        }


def _validated_document(source: Any):
    if isinstance(source, Mapping) or isinstance(source, (str, os.PathLike)):
        from pdfy.parser import load_document

        return load_document(source)
    if hasattr(source, "title") and hasattr(source, "sections"):
        return source
    raise TypeError("document deve ser um Document, Mapping, caminho ou JSON textual.")


def _write_trace_atomic(trace: LayoutTrace, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(trace.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=target.parent,
        prefix=f".{target.name}.", suffix=".tmp", delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def generate_pdf(
    document: Any,
    output: str | os.PathLike[str],
    *,
    trace_path: str | os.PathLike[str] | None = None,
) -> GenerationResult:
    """Validate and render a document to an atomically replaced PDF."""
    parsed = _validated_document(document)
    destination = Path(output).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_handle = tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp.pdf",
        delete=False,
    )
    temporary = Path(file_handle.name)
    file_handle.close()
    try:
        pdf = canvas.Canvas(
            str(temporary),
            pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
            pageCompression=1,
            invariant=1,
        )
        pdf.setTitle(str(value(parsed, "title", "Documento Matizze")))
        pdf.setAuthor("Matizze")
        pdf.setCreator("pdfy")
        pdf.setSubject(str(value(parsed, "subtitle", "Documento Matizze")))
        renderer = DocumentRenderer(pdf, paragraph_styles())
        trace = renderer.render(parsed)
        pdf.save()
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    if trace_path is not None:
        _write_trace_atomic(trace, Path(trace_path).expanduser().resolve())
    return GenerationResult(path=destination, trace=trace)


render_document = generate_pdf
