"""MCP STDIO server for discovering, validating and generating pdfy documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from pdfy import __version__
from pdfy.creation_options import CreationTopic, ExampleName, get_creation_options
from pdfy.engine import generate_pdf
from pdfy.errors import PdfyValidationError
from pdfy.parser import load_document
from pdfy.validation.pdf import (
    DEFAULT_RENDER_DPI,
    create_contact_sheet,
    inspect_pdf,
    pdfium_version,
    render_pdf,
)


def _validation_issues(error: PdfyValidationError) -> list[dict[str, Any]]:
    return [
        {
            "path": issue.path,
            "code": issue.code,
            "message": issue.message,
            "hint": issue.hint,
        }
        for issue in error.issues
    ]


def validate_document_payload(document: dict[str, Any]) -> dict[str, Any]:
    """Validate one JSON-compatible document without writing files."""

    try:
        parsed = load_document(document)
    except PdfyValidationError as error:
        return {"ok": False, "schema_version": "1", "issues": _validation_issues(error)}
    return {
        "ok": True,
        "schema_version": parsed.schema,
        "title": parsed.title,
        "mode": "content" if parsed.content is not None else "sections",
        "sections": len(parsed.sections),
        "components": sum(len(section.components) for section in parsed.sections),
        "content_characters": len(parsed.content or ""),
        "issues": [],
    }


def generate_document_payload(document: dict[str, Any], output_path: str) -> dict[str, Any]:
    """Generate, inspect and render one document, returning all artifact paths."""

    try:
        parsed = load_document(document)
    except PdfyValidationError as error:
        return {
            "ok": False,
            "stage": "document_validation",
            "issues": _validation_issues(error),
        }

    output = Path(output_path).expanduser().resolve()
    if output.suffix.casefold() != ".pdf":
        return {
            "ok": False,
            "stage": "arguments",
            "issues": [
                {
                    "path": "$.output_path",
                    "code": "file_extension",
                    "message": "output_path deve terminar em .pdf.",
                    "hint": None,
                }
            ],
        }

    trace_path = output.with_suffix(".layout.json")
    render_dir = output.parent / f"{output.stem}-render"
    result = generate_pdf(parsed, output, trace_path=trace_path)
    technical = inspect_pdf(result.path, document=parsed, layout_trace=result.trace)
    pages = render_pdf(result.path, render_dir, dpi=DEFAULT_RENDER_DPI)
    contact_sheet = create_contact_sheet(pages, render_dir / "contact-sheet.png")
    render_ok = len(pages) == technical.get("pages")
    issues = list(technical.get("issues", []))
    if not render_ok:
        issues.append(
            f"Foram renderizadas {len(pages)} páginas, mas o PDF registra "
            f"{technical.get('pages', 0)}."
        )
    return {
        "ok": bool(technical.get("ok")) and render_ok,
        "stage": "complete",
        "pdf": str(result.path),
        "layout_trace": str(trace_path),
        "pages": technical.get("pages"),
        "rendered_pages": [str(path.resolve()) for path in pages],
        "contact_sheet": str(contact_sheet.resolve()),
        "renderer": pdfium_version(),
        "issues": issues,
        "warnings": technical.get("warnings", []),
    }


mcp = MCPServer(
    "pdfy",
    title="pdfy",
    description="Gera PDFs A4 oficiais da Matizze a partir de conteúdo JSON estruturado.",
    instructions=(
        "Consulte pdfy_get_creation_options, valide o JSON com pdfy_validate_document "
        "e somente então gere o PDF com pdfy_generate_document. Não adicione opções visuais."
    ),
    version=__version__,
    log_level="WARNING",
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Descobrir opções de criação",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def pdfy_get_creation_options(
    topic: CreationTopic = "overview",
    component_type: str | None = None,
    example: ExampleName | None = None,
) -> dict[str, Any]:
    """Descobrir contrato, componentes, schema ou exemplos oficiais do pdfy.

    Use topic='overview' primeiro. Para detalhes de um componente, use
    topic='component' e component_type. Para o JSON Schema completo, use
    topic='schema'. Para um documento pronto, use topic='example' e escolha
    example='minimal', 'complete' ou 'markdown'.
    """

    return get_creation_options(topic, component_type, example)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Validar documento",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def pdfy_validate_document(document: dict[str, Any]) -> dict[str, Any]:
    """Validar o conteúdo JSON antes da geração, sem criar arquivos."""

    return validate_document_payload(document)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Gerar documento",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def pdfy_generate_document(document: dict[str, Any], output_path: str) -> dict[str, Any]:
    """Gerar e auditar o PDF, seus PNGs e a contact sheet no computador local."""

    return generate_document_payload(document, output_path)


def main() -> None:
    """Start the MCP server over STDIO."""

    mcp.run()


if __name__ == "__main__":
    main()
