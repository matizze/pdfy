"""Load, normalize and validate pdfy JSON documents."""

from __future__ import annotations

import json
import os
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pdfy.errors import PdfyValidationError, ValidationIssue
from pdfy.model import Component, Document, Section
from pdfy.validation.content import validate_content


class _DuplicateKeyError(ValueError):
    pass


class _NonFiniteNumberError(ValueError):
    pass


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise _NonFiniteNumberError(value)


def _parse_json(text: str, source_label: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except _DuplicateKeyError as error:
        raise PdfyValidationError(
            [ValidationIssue("$", "duplicate_key", f'chave JSON duplicada "{error.args[0]}".')]
        ) from None
    except _NonFiniteNumberError as error:
        raise PdfyValidationError(
            [ValidationIssue("$", "non_finite_number", f'número não finito "{error.args[0]}" não é JSON válido.')]
        ) from None
    except json.JSONDecodeError as error:
        message = f"JSON inválido em {source_label}, linha {error.lineno}, coluna {error.colno}: {error.msg}."
        raise PdfyValidationError([ValidationIssue("$", "invalid_json", message)]) from None


def _normalize(value: Any, path: tuple[Any, ...] = ()) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, item in value.items():
            if not isinstance(raw_key, str):
                raise PdfyValidationError(
                    [ValidationIssue("$", "invalid_key", "todas as chaves do documento devem ser strings.")]
                )
            key = unicodedata.normalize("NFC", raw_key)
            if key in result:
                raise PdfyValidationError(
                    [ValidationIssue("$", "duplicate_key", f'chave duplicada após normalização Unicode: "{key}".')]
                )
            result[key] = _normalize(item, path + (key,))
        return result
    if isinstance(value, (list, tuple)):
        return [_normalize(item, path + (index,)) for index, item in enumerate(value)]
    return value


def _build_document(data: dict[str, Any]) -> Document:
    sections = tuple(
        Section(
            title=section["title"],
            subtitle=section.get("subtitle"),
            components=tuple(Component.from_mapping(item) for item in section["components"]),
        )
        for section in data["sections"]
    )
    return Document(
        schema=data["schema"],
        title=data["title"],
        subtitle=data.get("subtitle"),
        recipient=data.get("recipient"),
        date=data.get("date"),
        sections=sections,
    )


def parse_document(data: Mapping[str, Any]) -> Document:
    """Validate an already loaded mapping and return an immutable model."""

    normalized = _normalize(data)
    issues = validate_content(normalized)
    if issues:
        raise PdfyValidationError(issues)
    return _build_document(normalized)


def load_document(source: Mapping[str, Any] | str | os.PathLike[str]) -> Document:
    """Load a mapping, a JSON string, or a UTF-8 JSON file."""

    if isinstance(source, Mapping):
        return parse_document(source)

    if isinstance(source, os.PathLike):
        path = Path(source)
        raw_json = _read_path(path)
        return parse_document(_parse_json(raw_json, str(path)))

    if not isinstance(source, str):
        raise TypeError("source must be a mapping, JSON string, or path-like object")

    stripped = source.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return parse_document(_parse_json(source, "texto de entrada"))

    path = Path(source)
    raw_json = _read_path(path)
    return parse_document(_parse_json(raw_json, str(path)))


def _read_path(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise PdfyValidationError(
            [ValidationIssue("$", "file_not_found", f'arquivo de entrada não encontrado: "{path}".')]
        ) from None
    except UnicodeDecodeError as error:
        raise PdfyValidationError(
            [ValidationIssue("$", "encoding", f'arquivo "{path}" não está em UTF-8: {error}.')]
        ) from None
    except OSError as error:
        raise PdfyValidationError(
            [ValidationIssue("$", "read_error", f'não foi possível ler "{path}": {error}.')]
        ) from None


validate_document = load_document
