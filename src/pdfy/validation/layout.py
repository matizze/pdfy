"""Validation helpers for renderer layout traces.

The PDF renderer is responsible for recording the coordinates that it actually
draws.  This module deliberately does not know about component styling; it only
checks page geometry, declared safe areas, pagination roles and opt-in collision
groups.  Post-render PDF inspection in :mod:`pdfy.validation.pdf` complements
these checks.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any


A4_WIDTH = 595.2755905511812
A4_HEIGHT = 841.8897637795277
DEFAULT_TOLERANCE_PT = 0.75


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if is_dataclass(value):
        return _plain(asdict(value))
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump())
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if hasattr(value, "__dict__"):
        return {
            key: _plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _bbox(value: Any) -> tuple[float, float, float, float] | None:
    value = _plain(value)
    if isinstance(value, Mapping):
        keys = ("x0", "y0", "x1", "y1")
        if all(key in value for key in keys):
            value = [value[key] for key in keys]
        elif all(key in value for key in ("x", "y", "width", "height")):
            try:
                x = float(value["x"])
                y = float(value["y"])
                value = [x, y, x + float(value["width"]), y + float(value["height"])]
            except (TypeError, ValueError):
                return None
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        result = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        return None
    if result[0] > result[2] or result[1] > result[3]:
        return None
    return result


def _outside(
    inner: tuple[float, float, float, float],
    outer: tuple[float, float, float, float],
    tolerance: float,
) -> bool:
    return (
        inner[0] < outer[0] - tolerance
        or inner[1] < outer[1] - tolerance
        or inner[2] > outer[2] + tolerance
        or inner[3] > outer[3] + tolerance
    )


def _intersection_area(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    width = min(first[2], second[2]) - max(first[0], second[0])
    height = min(first[3], second[3]) - max(first[1], second[1])
    return max(0.0, width) * max(0.0, height)


def _iter_pages(trace: Any) -> list[dict[str, Any]]:
    value = _plain(trace)
    if value is None:
        return []
    if isinstance(value, Mapping):
        pages = value.get("pages", [])
    else:
        pages = getattr(value, "pages", [])
    pages = _plain(pages)
    if not isinstance(pages, list):
        return []
    return [dict(page) for page in pages if isinstance(page, Mapping)]


def section_start_pages(trace: Any) -> list[int]:
    """Return section start page numbers from a renderer trace."""

    starts: list[int] = []
    for page in _iter_pages(trace):
        if page.get("role") != "section":
            continue
        try:
            starts.append(int(page.get("number")))
        except (TypeError, ValueError):
            continue
    return starts


def validate_layout_trace(
    trace: Any,
    *,
    page_count: int | None = None,
    expected_sections: int | None = None,
    tolerance: float = DEFAULT_TOLERANCE_PT,
) -> dict[str, Any]:
    """Validate a ``LayoutTrace``-like object and return a JSON-safe report.

    Expected traces contain ``pages``.  Each page may contain ``safe_area`` and
    ``items`` with PDF-coordinate bboxes. Content items are checked against one
    another by default. Other zones can opt in by sharing a non-empty
    ``collision_group``; decorative overlays therefore avoid false positives.
    """

    issues: list[str] = []
    warnings: list[str] = []
    pages = _iter_pages(trace)
    if trace is None:
        warnings.append("Layout trace não fornecido; validação geométrica interna ignorada.")
        return {
            "ok": True,
            "available": False,
            "issues": issues,
            "warnings": warnings,
            "page_count": 0,
            "section_start_pages": [],
            "items_checked": 0,
        }
    if not pages:
        issues.append("Layout trace não contém páginas válidas.")

    numbers: list[int] = []
    roles: list[str] = []
    checked = 0
    page_bounds = (0.0, 0.0, A4_WIDTH, A4_HEIGHT)

    for fallback_number, page in enumerate(pages, 1):
        try:
            number = int(page.get("number", fallback_number))
        except (TypeError, ValueError):
            issues.append(f"Trace página {fallback_number}: número inválido.")
            number = fallback_number
        numbers.append(number)
        role = str(page.get("role", ""))
        roles.append(role)
        if role not in {"cover", "section", "continuation", "content", "closing"}:
            issues.append(f"Trace página {number}: role inválido '{role}'.")

        safe_area = _bbox(page.get("safe_area"))
        if safe_area is not None and _outside(safe_area, page_bounds, tolerance):
            issues.append(f"Trace página {number}: safe_area fora do A4.")

        raw_items = page.get("items", [])
        items = raw_items if isinstance(raw_items, list) else []
        collision_groups: dict[str, list[tuple[int, tuple[float, float, float, float]]]] = {}
        for item_index, raw_item in enumerate(items):
            item = _plain(raw_item)
            if not isinstance(item, Mapping):
                issues.append(f"Trace página {number}, item {item_index}: item inválido.")
                continue
            bounds = _bbox(item.get("bbox"))
            if bounds is None:
                issues.append(f"Trace página {number}, item {item_index}: bbox inválida.")
                continue
            checked += 1
            kind = str(item.get("kind", "item"))
            zone = str(item.get("zone", "content"))
            allowed = _bbox(item.get("allowed_bbox"))
            if allowed is None:
                allowed = (
                    page_bounds
                    if zone != "content" or kind in {"background", "full_bleed"}
                    else safe_area
                )
            if allowed is None:
                allowed = page_bounds
            if _outside(bounds, page_bounds, tolerance):
                issues.append(
                    f"Trace página {number}, item {item_index} ({kind}): bbox fora do A4."
                )
            elif _outside(bounds, allowed, tolerance):
                issues.append(
                    f"Trace página {number}, item {item_index} ({kind}): "
                    "bbox fora da área permitida."
                )

            group = item.get("collision_group")
            if group is None and zone == "content":
                group = "__content__"
            if group and not item.get("allow_overlap", False):
                collision_groups.setdefault(str(group), []).append((item_index, bounds))

        for group, candidates in collision_groups.items():
            for offset, (first_index, first) in enumerate(candidates):
                for second_index, second in candidates[offset + 1 :]:
                    area = _intersection_area(first, second)
                    if area > 1.0:
                        issues.append(
                            f"Trace página {number}: itens {first_index} e {second_index} "
                            f"se sobrepõem no grupo '{group}' ({area:.2f} pt²)."
                        )

    expected_numbers = list(range(1, len(pages) + 1))
    if numbers and numbers != expected_numbers:
        issues.append("Layout trace tem numeração de páginas não sequencial.")
    if page_count is not None and len(pages) != page_count:
        issues.append(
            f"Layout trace registra {len(pages)} páginas, mas o PDF contém {page_count}."
        )
    if roles:
        if roles[0] != "cover":
            issues.append("A primeira página do trace não é a capa.")
        if roles[-1] != "closing":
            issues.append("A última página do trace não é o encerramento.")

    starts = section_start_pages(trace)
    if starts != sorted(set(starts)):
        issues.append("Páginas iniciais de seção não são únicas e crescentes.")
    if expected_sections is not None and len(starts) != expected_sections:
        issues.append(
            f"Trace registra {len(starts)} inícios de seção; esperado: {expected_sections}."
        )

    return {
        "ok": not issues,
        "available": True,
        "issues": issues,
        "warnings": warnings,
        "page_count": len(pages),
        "section_start_pages": starts,
        "items_checked": checked,
    }


__all__ = [
    "A4_HEIGHT",
    "A4_WIDTH",
    "DEFAULT_TOLERANCE_PT",
    "section_start_pages",
    "validate_layout_trace",
]
