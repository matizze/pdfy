"""Public validation errors for pdfy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One actionable problem found in a document."""

    path: str
    code: str
    message: str
    hint: str | None = None

    def __str__(self) -> str:
        rendered = f"{self.path}: {self.message}"
        if self.hint:
            rendered += f" {self.hint}"
        return rendered


class PdfyValidationError(ValueError):
    """Raised when input cannot be safely rendered by pdfy."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        unique = {
            (issue.path, issue.code, issue.message, issue.hint): issue
            for issue in issues
        }
        self.issues = tuple(
            sorted(unique.values(), key=lambda item: (item.path, item.code, item.message))
        )
        if not self.issues:
            raise ValueError("PdfyValidationError requires at least one issue")
        count = len(self.issues)
        noun = "problema" if count == 1 else "problemas"
        details = "\n".join(f"- {issue}" for issue in self.issues)
        super().__init__(f"Documento inválido: {count} {noun}.\n{details}")
