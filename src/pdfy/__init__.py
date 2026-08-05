"""API pública mínima do pdfy."""

from .engine import GenerationResult, generate_pdf
from .errors import PdfyValidationError, ValidationIssue
from .parser import validate_document

__all__ = [
    "GenerationResult",
    "PdfyValidationError",
    "ValidationIssue",
    "generate_pdf",
    "validate_document",
]

__version__ = "0.1.0"
