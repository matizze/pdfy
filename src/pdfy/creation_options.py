"""Canonical, machine-readable discovery of the public pdfy content contract."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

from pdfy.registry import supported_component_types
from pdfy.validation.content import load_schema


CreationTopic = Literal["overview", "component", "schema", "example"]
ExampleName = Literal["minimal", "complete"]

_SOURCE_EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

COMPONENT_PURPOSES = {
    "text": "Parágrafos e explicações em texto corrido.",
    "metrics": "Indicadores curtos formados por rótulo, valor e nota opcional.",
    "highlights": "Mensagens breves que precisam de ênfase equivalente.",
    "cards": "Conjunto de conceitos ou entregas com título e descrição.",
    "callout": "Uma decisão, conclusão ou mensagem dominante.",
    "comparison": "Contraste linha a linha entre dois cenários.",
    "chart": "Valores numéricos comparáveis em barras horizontais.",
    "steps": "Sequência ordenada de ações com numeração automática.",
    "timeline": "Marcos associados a períodos ou fases.",
    "table": "Dados tabulares com duas a seis colunas.",
    "investment": "Itens de investimento, total e observações sem cálculo automático.",
    "list": "Itens simples sem progressão obrigatória.",
    "signature": "Bloco de assinatura para até quatro signatários.",
}


def _load_example(name: ExampleName) -> dict[str, Any]:
    packaged = files("pdfy").joinpath("examples").joinpath(f"{name}-document.json")
    if packaged.is_file():
        with packaged.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    with (_SOURCE_EXAMPLES / f"{name}-document.json").open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _component_example(document: dict[str, Any], component_type: str) -> dict[str, Any] | None:
    for section in document.get("sections", []):
        for component in section.get("components", []):
            if component.get("type") == component_type:
                return component
    return None


def _referenced_definitions(definition: dict[str, Any], definitions: dict[str, Any]) -> dict[str, Any]:
    found: dict[str, Any] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                name = reference.rsplit("/", 1)[-1]
                if name not in found and name in definitions:
                    found[name] = definitions[name]
                    visit(definitions[name])
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(definition)
    return found


def get_creation_options(
    topic: CreationTopic = "overview",
    component_type: str | None = None,
    example: ExampleName | None = None,
) -> dict[str, Any]:
    """Return the official content choices without exposing visual controls."""

    schema = load_schema()
    if topic == "overview":
        root = schema["properties"]
        required = schema["required"]
        return {
            "schema_version": "1",
            "contract": {
                "required_fields": required,
                "optional_fields": [name for name in root if name not in required],
                "section_required_fields": schema["$defs"]["section"]["required"],
                "automatic_pages": ["cover", "closing"],
                "each_section_starts_on_new_page": True,
                "visual_properties_allowed": False,
            },
            "components": [
                {"type": name, "use_for": COMPONENT_PURPOSES[name]}
                for name in supported_component_types()
            ],
            "recommended_flow": [
                "Escolher os componentes adequados ao conteúdo.",
                "Consultar topic='component' quando precisar dos campos e limites de um tipo.",
                "Montar o documento JSON.",
                "Executar pdfy_validate_document.",
                "Corrigir todos os erros antes de executar pdfy_generate_document.",
            ],
        }

    if topic == "schema":
        return {"schema_version": "1", "json_schema": schema}

    if topic == "example":
        selected = example or "minimal"
        return {"schema_version": "1", "example": selected, "document": _load_example(selected)}

    if topic == "component":
        if component_type is None:
            raise ValueError("component_type é obrigatório quando topic='component'.")
        if component_type not in supported_component_types():
            allowed = ", ".join(supported_component_types())
            raise ValueError(f"Componente desconhecido: {component_type!r}. Permitidos: {allowed}.")
        definition = schema["$defs"][component_type]
        required = definition["required"]
        properties = definition["properties"]
        return {
            "schema_version": "1",
            "component_type": component_type,
            "use_for": COMPONENT_PURPOSES[component_type],
            "required_fields": required,
            "optional_fields": [name for name in properties if name not in required],
            "definition": definition,
            "referenced_definitions": _referenced_definitions(definition, schema["$defs"]),
            "example": _component_example(_load_example("complete"), component_type),
            "visual_properties_allowed": False,
        }

    raise ValueError(f"Tópico desconhecido: {topic!r}.")


__all__ = ["CreationTopic", "ExampleName", "get_creation_options"]
