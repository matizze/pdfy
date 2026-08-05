"""JSON Schema and semantic validation for document content."""

from __future__ import annotations

import math
import re
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from pdfy.errors import ValidationIssue


COMPONENT_TYPES = (
    "callout",
    "cards",
    "chart",
    "comparison",
    "highlights",
    "investment",
    "list",
    "metrics",
    "signature",
    "steps",
    "table",
    "text",
    "timeline",
)

_SOURCE_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "document.schema.json"
_UNEXPECTED_PROPERTY = re.compile(r"\('([^']+)' was unexpected\)")


def load_schema() -> dict[str, Any]:
    import json

    packaged = files("pdfy").joinpath("schema").joinpath("document.schema.json")
    if packaged.is_file():
        with packaged.open("r", encoding="utf-8") as stream:
            schema = json.load(stream)
    else:
        with _SOURCE_SCHEMA_PATH.open("r", encoding="utf-8") as stream:
            schema = json.load(stream)
    Draft202012Validator.check_schema(schema)
    return schema


def format_path(parts: list[Any] | tuple[Any, ...]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        elif isinstance(part, str) and part.isidentifier():
            path += f".{part}"
        else:
            escaped = str(part).replace("\\", "\\\\").replace("'", "\\'")
            path += f"['{escaped}']"
    return path


def _issue_from_error(error: ValidationError, prefix: tuple[Any, ...] = ()) -> ValidationIssue:
    parts = prefix + tuple(error.absolute_path if not prefix else error.path)
    path = format_path(parts)
    validator = error.validator
    value = error.instance

    if validator == "required":
        missing = error.message.split("'")[1]
        return ValidationIssue(path, "required", f'campo obrigatório "{missing}" ausente.')
    if validator == "additionalProperties":
        match = _UNEXPECTED_PROPERTY.search(error.message)
        field = match.group(1) if match else "desconhecido"
        hint = None
        if field in {"color", "font", "kind", "layout", "size", "style", "template", "tone"}:
            hint = "A apresentação visual é controlada pelo pdfy."
        return ValidationIssue(
            f"{path}.{field}",
            "unexpected_property",
            "campo não permitido.",
            hint,
        )
    if validator == "const":
        return ValidationIssue(path, "const", f"valor esperado {error.validator_value!r}; recebido {value!r}.")
    if validator == "type":
        return ValidationIssue(path, "type", f"tipo inválido; esperado {error.validator_value}, recebido {type(value).__name__}.")
    if validator == "pattern":
        return ValidationIssue(path, "format", "formato inválido; use YYYY-MM-DD.")
    if validator == "minLength":
        return ValidationIssue(path, "too_short", "texto vazio não é permitido.")
    if validator == "maxLength":
        return ValidationIssue(path, "too_long", f"texto excede o limite de {error.validator_value} caracteres.")
    if validator == "minItems":
        return ValidationIssue(path, "too_few_items", f"informe ao menos {error.validator_value} item(ns).")
    if validator == "maxItems":
        return ValidationIssue(path, "too_many_items", f"limite de {error.validator_value} item(ns) excedido.")
    if validator in {"minimum", "maximum"}:
        relation = "maior ou igual a" if validator == "minimum" else "menor ou igual a"
        return ValidationIssue(path, "number_range", f"o número deve ser {relation} {error.validator_value}.")
    return ValidationIssue(path, "schema", error.message)


def _component_issues(error: ValidationError, schema: dict[str, Any]) -> list[ValidationIssue]:
    component = error.instance
    prefix = tuple(error.absolute_path)
    if not isinstance(component, dict):
        return [ValidationIssue(format_path(prefix), "type", "componente deve ser um objeto JSON.")]

    component_type = component.get("type")
    type_path = format_path(prefix + ("type",))
    if not isinstance(component_type, str):
        return [ValidationIssue(type_path, "required", 'campo obrigatório "type" ausente ou inválido.')]
    if component_type not in COMPONENT_TYPES:
        allowed = ", ".join(COMPONENT_TYPES)
        return [
            ValidationIssue(
                type_path,
                "unknown_component",
                f'componente desconhecido "{component_type}".',
                f"Permitidos: {allowed}.",
            )
        ]

    selected = {
        "$ref": f"#/$defs/{component_type}",
        "$defs": schema["$defs"],
    }
    validator = Draft202012Validator(selected)
    return [_issue_from_error(item, prefix) for item in validator.iter_errors(component)]


def schema_issues(data: Any) -> list[ValidationIssue]:
    schema = load_schema()
    validator = Draft202012Validator(schema)
    issues: list[ValidationIssue] = []
    for error in validator.iter_errors(data):
        error_path = tuple(error.absolute_path)
        is_component_dispatch = (
            len(error_path) == 4
            and error_path[0] == "sections"
            and error_path[2] == "components"
        )
        if error.validator == "oneOf" and is_component_dispatch:
            issues.extend(_component_issues(error, schema))
        else:
            issues.append(_issue_from_error(error))
    return issues


def _walk_numbers(value: Any, path: tuple[Any, ...] = ()) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if isinstance(value, float) and not math.isfinite(value):
        issues.append(ValidationIssue(format_path(path), "non_finite_number", "número deve ser finito."))
    elif isinstance(value, dict):
        for key, item in value.items():
            issues.extend(_walk_numbers(item, path + (key,)))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            issues.extend(_walk_numbers(item, path + (index,)))
    return issues


def semantic_issues(data: Any) -> list[ValidationIssue]:
    issues = _walk_numbers(data)
    if not isinstance(data, dict):
        return issues

    value = data.get("date")
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            date.fromisoformat(value)
        except ValueError:
            issues.append(
                ValidationIssue(
                    "$.date",
                    "invalid_date",
                    f'data inválida "{value}"; use uma data real no formato YYYY-MM-DD.',
                )
            )

    sections = data.get("sections")
    if not isinstance(sections, list):
        return issues
    for section_index, section in enumerate(sections):
        if not isinstance(section, dict) or not isinstance(section.get("components"), list):
            continue
        for component_index, component in enumerate(section["components"]):
            if not isinstance(component, dict) or component.get("type") != "table":
                continue
            columns = component.get("columns")
            rows = component.get("rows")
            if not isinstance(columns, list) or not isinstance(rows, list):
                continue
            for row_index, row in enumerate(rows):
                if isinstance(row, list) and len(row) != len(columns):
                    path = f"$.sections[{section_index}].components[{component_index}].rows[{row_index}]"
                    issues.append(
                        ValidationIssue(
                            path,
                            "table_width",
                            f"esperadas {len(columns)} células, recebidas {len(row)}.",
                        )
                    )
    return issues


def validate_content(data: Any) -> list[ValidationIssue]:
    """Return all schema and semantic issues in deterministic order."""

    return schema_issues(data) + semantic_issues(data)
