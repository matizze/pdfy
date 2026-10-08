"""Immutable, renderer-friendly document model."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def freeze(value: Any) -> Any:
    """Recursively freeze JSON-compatible data without changing scalar values."""

    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    return value


def thaw(value: Any) -> Any:
    """Return a mutable JSON-compatible copy of frozen model data."""

    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class Component(Mapping[str, Any]):
    """A validated component that also behaves like a read-only mapping."""

    type: str
    data: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Component:
        frozen = freeze(data)
        return cls(type=str(frozen["type"]), data=frozen)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def to_dict(self) -> dict[str, Any]:
        return thaw(self.data)


@dataclass(frozen=True, slots=True)
class Section:
    title: str
    subtitle: str | None
    components: tuple[Component, ...]

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "title": self.title,
            "components": [component.to_dict() for component in self.components],
        }
        if self.subtitle is not None:
            result["subtitle"] = self.subtitle
        return result


@dataclass(frozen=True, slots=True)
class Document:
    schema: str
    title: str
    subtitle: str | None
    recipient: str | None
    date: str | None
    sections: tuple[Section, ...]
    content: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema": self.schema,
            "title": self.title,
        }
        for key in ("subtitle", "recipient", "date"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        if self.content is not None:
            result["content"] = self.content
        if self.sections:
            result["sections"] = [section.to_dict() for section in self.sections]
        return result
