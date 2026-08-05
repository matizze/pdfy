from __future__ import annotations

import asyncio
from pathlib import Path

from mcp import Client

from pdfy.creation_options import get_creation_options
from pdfy.mcp_server import (
    generate_document_payload,
    mcp,
    validate_document_payload,
)


def _minimal_document() -> dict:
    return {
        "schema": "1",
        "title": "Documento criado pelo MCP",
        "sections": [
            {
                "title": "Resumo",
                "components": [{"type": "text", "content": "Conteúdo validado."}],
            }
        ],
    }


def test_creation_options_cover_overview_components_schema_and_examples() -> None:
    overview = get_creation_options()
    component = get_creation_options("component", "metrics")
    schema = get_creation_options("schema")
    example = get_creation_options("example", example="complete")

    assert overview["contract"]["visual_properties_allowed"] is False
    assert len(overview["components"]) == 13
    assert component["required_fields"] == ["type", "items"]
    assert component["example"]["type"] == "metrics"
    assert schema["json_schema"]["properties"]["schema"]["const"] == "1"
    assert example["document"]["sections"]


def test_mcp_validation_returns_all_actionable_issues() -> None:
    document = _minimal_document()
    document["sections"][0]["components"][0]["color"] = "#000000"

    report = validate_document_payload(document)

    assert report["ok"] is False
    assert report["issues"][0]["path"].endswith(".color")
    assert report["issues"][0]["hint"]


def test_mcp_generation_audits_and_renders_locally(tmp_path: Path) -> None:
    report = generate_document_payload(_minimal_document(), str(tmp_path / "mcp.pdf"))

    assert report["ok"], report["issues"]
    assert Path(report["pdf"]).is_file()
    assert Path(report["layout_trace"]).is_file()
    assert Path(report["contact_sheet"]).is_file()
    assert len(report["rendered_pages"]) == 3
    assert report["renderer"].startswith("pypdfium2")


def test_mcp_exposes_exactly_the_three_public_tools() -> None:
    async def exercise() -> None:
        async with Client(mcp) as client:
            listed = await client.list_tools()
            assert {tool.name for tool in listed.tools} == {
                "pdfy_get_creation_options",
                "pdfy_validate_document",
                "pdfy_generate_document",
            }
            annotations = {tool.name: tool.annotations for tool in listed.tools}
            assert annotations["pdfy_get_creation_options"].read_only_hint is True
            assert annotations["pdfy_generate_document"].destructive_hint is True
            called = await client.call_tool("pdfy_get_creation_options", {"topic": "overview"})
            assert called.structured_content["contract"]["visual_properties_allowed"] is False

    asyncio.run(exercise())
