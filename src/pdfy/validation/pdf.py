"""Technical inspection, rendering and visual regression for generated PDFs."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat
from pypdf import PdfReader

from pdfy.validation.layout import (
    A4_HEIGHT,
    A4_WIDTH,
    DEFAULT_TOLERANCE_PT,
    validate_layout_trace,
)


DEFAULT_RENDER_DPI = 144
GOLDEN_BORDER_PX = 2
GOLDEN_MAX_MAE = 1.5
GOLDEN_PIXEL_DELTA = 32
GOLDEN_MAX_CHANGED_FRACTION = 0.005
MINIMUM_TEXT_SIZE_PT = 6.25
BODY_TEXT_SIZE_PT = 8.0


class PdfValidationDependencyError(RuntimeError):
    """Raised when a required external validation dependency is unavailable."""


def _normalise_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def _document_value(document: Any, name: str, default: Any = None) -> Any:
    if document is None:
        return default
    if isinstance(document, Mapping):
        return document.get(name, default)
    return getattr(document, name, default)


def _sections(document: Any) -> list[Any]:
    value = _document_value(document, "sections", [])
    return list(value) if isinstance(value, Sequence) else []


def _section_title(section: Any) -> str:
    if isinstance(section, Mapping):
        return str(section.get("title", ""))
    return str(getattr(section, "title", ""))


def _resolve(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def _font_descriptor(font: Any) -> Any:
    font = _resolve(font)
    descriptor = _resolve(font.get("/FontDescriptor")) if hasattr(font, "get") else None
    if descriptor:
        return descriptor
    descendants = _resolve(font.get("/DescendantFonts")) if hasattr(font, "get") else None
    if descendants:
        descendant = _resolve(descendants[0])
        return _resolve(descendant.get("/FontDescriptor"))
    return None


def _font_records(reader: PdfReader) -> list[dict[str, Any]]:
    records: dict[tuple[str, bool], dict[str, Any]] = {}
    visited_resources: set[int] = set()

    def visit(resources: Any) -> None:
        resources = _resolve(resources)
        if not isinstance(resources, Mapping):
            return
        marker = id(resources)
        if marker in visited_resources:
            return
        visited_resources.add(marker)
        fonts = _resolve(resources.get("/Font", {}))
        if isinstance(fonts, Mapping):
            for font_ref in fonts.values():
                font = _resolve(font_ref)
                if not isinstance(font, Mapping):
                    continue
                name = str(font.get("/BaseFont", ""))
                descriptor = _font_descriptor(font)
                embedded = bool(
                    descriptor
                    and any(descriptor.get(key) is not None for key in ("/FontFile", "/FontFile2", "/FontFile3"))
                )
                records[(name, embedded)] = {"name": name, "embedded": embedded}
        xobjects = _resolve(resources.get("/XObject", {}))
        if isinstance(xobjects, Mapping):
            for xobject_ref in xobjects.values():
                xobject = _resolve(xobject_ref)
                if isinstance(xobject, Mapping):
                    visit(xobject.get("/Resources"))

    for page in reader.pages:
        visit(page.get("/Resources"))
    return sorted(records.values(), key=lambda item: (item["name"], item["embedded"]))


def _object_outside_page(obj: Mapping[str, Any], width: float, height: float) -> bool:
    try:
        x0 = float(obj.get("x0", 0.0))
        x1 = float(obj.get("x1", width))
        top = float(obj.get("top", 0.0))
        bottom = float(obj.get("bottom", height))
    except (TypeError, ValueError):
        return False
    tolerance = DEFAULT_TOLERANCE_PT
    return x0 < -tolerance or x1 > width + tolerance or top < -tolerance or bottom > height + tolerance


def _covers_page(obj: Mapping[str, Any], width: float, height: float) -> bool:
    """Return whether a raster object intentionally covers the complete page."""

    try:
        return (
            float(obj.get("x0", width)) <= DEFAULT_TOLERANCE_PT
            and float(obj.get("x1", 0.0)) >= width - DEFAULT_TOLERANCE_PT
            and float(obj.get("top", height)) <= DEFAULT_TOLERANCE_PT
            and float(obj.get("bottom", 0.0)) >= height - DEFAULT_TOLERANCE_PT
        )
    except (TypeError, ValueError):
        return False


def _find_section_start_pages(page_texts: list[str], section_titles: list[str]) -> tuple[list[int], list[str]]:
    starts: list[int] = []
    missing: list[str] = []
    cursor = 1  # page index 0 is the automatic cover
    normalised_pages = [_normalise_text(text) for text in page_texts]
    for title in section_titles:
        needle = _normalise_text(title)
        found: int | None = None
        for page_index in range(cursor, max(cursor, len(normalised_pages) - 1)):
            if needle and needle in normalised_pages[page_index]:
                found = page_index + 1
                break
        if found is None:
            missing.append(title)
            continue
        starts.append(found)
        cursor = found  # next search starts on the following zero-based page index
    return starts, missing


def inspect_pdf(
    pdf_path: str | Path,
    *,
    document: Any = None,
    layout_trace: Any = None,
) -> dict[str, Any]:
    """Inspect a generated PDF and return a machine-readable report."""

    path = Path(pdf_path)
    issues: list[str] = []
    warnings: list[str] = []
    if not path.is_file():
        return {
            "ok": False,
            "pdf": str(path),
            "issues": [f"PDF não encontrado: {path}"],
            "warnings": warnings,
        }

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pypdf exposes several parser exception types
        return {
            "ok": False,
            "pdf": str(path.resolve()),
            "issues": [f"PDF inválido ou ilegível: {exc}"],
            "warnings": warnings,
        }

    if reader.is_encrypted:
        issues.append("PDF está criptografado.")
    page_count = len(reader.pages)
    sections = _sections(document)
    minimum_pages = max(len(sections) + 2, 3) if document is not None else 3
    if page_count < minimum_pages:
        issues.append(f"PDF contém {page_count} páginas; mínimo esperado: {minimum_pages}.")

    metadata = reader.metadata
    metadata_title = str(getattr(metadata, "title", "") or "")
    expected_title = str(_document_value(document, "title", "") or "")
    if expected_title and metadata_title != expected_title:
        issues.append(
            f"Metadado title divergente: esperado '{expected_title}', recebido '{metadata_title}'."
        )

    page_geometry: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, 1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        rotation = int(page.get("/Rotate", 0) or 0) % 360
        a4 = math.isclose(width, A4_WIDTH, abs_tol=DEFAULT_TOLERANCE_PT) and math.isclose(
            height, A4_HEIGHT, abs_tol=DEFAULT_TOLERANCE_PT
        )
        if not a4:
            issues.append(f"Página {index}: MediaBox não é A4 ({width:.2f} × {height:.2f} pt).")
        if rotation:
            issues.append(f"Página {index}: rotação inesperada de {rotation} graus.")
        crop_width = float(page.cropbox.width)
        crop_height = float(page.cropbox.height)
        if not (
            math.isclose(crop_width, width, abs_tol=DEFAULT_TOLERANCE_PT)
            and math.isclose(crop_height, height, abs_tol=DEFAULT_TOLERANCE_PT)
        ):
            warnings.append(f"Página {index}: CropBox difere do MediaBox.")
        page_geometry.append(
            {"page": index, "width": width, "height": height, "rotation": rotation, "a4": a4}
        )

    fonts = _font_records(reader)
    embedded_montserrat = [
        item for item in fonts if "montserrat" in item["name"].casefold() and item["embedded"]
    ]
    if not embedded_montserrat:
        issues.append("Nenhuma fonte Montserrat incorporada foi encontrada.")
    page_stats: list[dict[str, Any]] = []
    page_texts: list[str] = []
    replacement_found = False
    used_font_names: set[str] = set()
    with pdfplumber.open(str(path)) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            page_texts.append(text)
            if "\ufffd" in text or "\x00" in text:
                replacement_found = True
            used_font_names.update(str(char.get("fontname", "")) for char in page.chars)
            out_chars = [
                char for char in page.chars if _object_outside_page(char, page.width, page.height)
            ]
            too_small = [
                char for char in page.chars if float(char.get("size", BODY_TEXT_SIZE_PT)) < MINIMUM_TEXT_SIZE_PT
            ]
            under_body = [
                char
                for char in page.chars
                if MINIMUM_TEXT_SIZE_PT
                <= float(char.get("size", BODY_TEXT_SIZE_PT))
                < BODY_TEXT_SIZE_PT
            ]
            if out_chars:
                issues.append(f"Página {index}: {len(out_chars)} caracteres fora do MediaBox.")
            if too_small:
                issues.append(
                    f"Página {index}: {len(too_small)} caracteres abaixo de {MINIMUM_TEXT_SIZE_PT:g} pt."
                )
            if under_body:
                warnings.append(
                    f"Página {index}: {len(under_body)} caracteres abaixo de 8 pt; "
                    "devem ser apenas labels ou rodapé."
                )
            out_objects = 0
            for collection_name in ("images", "rects", "curves", "lines"):
                collection = getattr(page, collection_name, [])
                out_objects += sum(
                    1
                    for item in collection
                    if _object_outside_page(item, page.width, page.height)
                    and not (
                        collection_name == "images"
                        and _covers_page(item, page.width, page.height)
                    )
                )
            if out_objects:
                issues.append(f"Página {index}: {out_objects} objetos gráficos fora do MediaBox.")
            page_stats.append(
                {
                    "page": index,
                    "characters": len(page.chars),
                    "out_of_bounds_characters": len(out_chars),
                    "out_of_bounds_objects": out_objects,
                    "minimum_font_size": min(
                        (float(char.get("size", 0.0)) for char in page.chars), default=None
                    ),
                    "under_body_size_characters": len(under_body),
                }
            )
    if replacement_found:
        issues.append("Texto extraído contém caractere de substituição ou NUL.")
    non_embedded_used = [
        item["name"]
        for item in fonts
        if not item["embedded"]
        and any(
            item["name"].lstrip("/").casefold() in used.casefold()
            for used in used_font_names
        )
    ]
    if non_embedded_used:
        issues.append("Fontes usadas e não incorporadas: " + ", ".join(non_embedded_used) + ".")

    if expected_title and (not page_texts or _normalise_text(expected_title) not in _normalise_text(page_texts[0])):
        issues.append("A capa automática não contém o título do documento.")
    if page_texts and len(page_texts[-1].strip()) < 8:
        issues.append("A última página não contém o encerramento esperado.")

    titles = [_section_title(section) for section in sections]
    inferred_starts, missing_titles = _find_section_start_pages(page_texts, titles)
    if missing_titles:
        issues.append("Títulos de seção ausentes no PDF: " + ", ".join(missing_titles) + ".")
    if inferred_starts and inferred_starts != sorted(set(inferred_starts)):
        issues.append("Mais de uma seção parece começar na mesma página.")

    layout = validate_layout_trace(
        layout_trace,
        page_count=page_count,
        expected_sections=len(sections) if document is not None else None,
    )
    issues.extend(layout["issues"])
    warnings.extend(layout["warnings"])

    return {
        "ok": not issues,
        "pdf": str(path.resolve()),
        "file_size": path.stat().st_size,
        "pages": page_count,
        "metadata": {
            "title": metadata_title,
            "author": str(getattr(metadata, "author", "") or ""),
            "creator": str(getattr(metadata, "creator", "") or ""),
        },
        "fonts": fonts,
        "geometry": page_geometry,
        "page_stats": page_stats,
        "section_start_pages": layout["section_start_pages"] or inferred_starts,
        "layout": layout,
        "issues": issues,
        "warnings": warnings,
    }


def pdfium_version() -> str:
    """Return the bundled renderer versions used for reproducible previews."""

    return f"pypdfium2 {pdfium.PYPDFIUM_INFO}; PDFium {pdfium.PDFIUM_INFO}"


def render_pdf(
    pdf_path: str | Path,
    render_dir: str | Path,
    *,
    dpi: int = DEFAULT_RENDER_DPI,
) -> list[Path]:
    """Render every page through the bundled PDFium and return ordered PNGs."""

    pdf = Path(pdf_path)
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {pdf}")
    if dpi < 72 or dpi > 600:
        raise ValueError("dpi deve estar entre 72 e 600.")
    output_dir = Path(render_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("page-*.png"):
        stale.unlink()

    pages: list[Path] = []
    document = pdfium.PdfDocument(str(pdf))
    try:
        scale = dpi / 72
        for index in range(len(document)):
            page = document[index]
            bitmap = None
            try:
                bitmap = page.render(scale=scale, rotation=0)
                image = bitmap.to_pil().convert("RGB")
                try:
                    target = output_dir / f"page-{index + 1:03d}.png"
                    image.save(target, format="PNG", optimize=False)
                    pages.append(target)
                finally:
                    image.close()
            finally:
                if bitmap is not None:
                    bitmap.close()
                page.close()
    except Exception as exc:
        for generated in pages:
            generated.unlink(missing_ok=True)
        raise RuntimeError(f"PDFium não conseguiu renderizar o PDF: {exc}") from exc
    finally:
        document.close()
    if not pages:
        raise RuntimeError("PDFium não produziu imagens para o PDF.")
    return pages


def create_contact_sheet(
    images: Sequence[str | Path],
    output_path: str | Path,
    *,
    thumbnail_width: int = 360,
    columns: int = 4,
) -> Path:
    """Create a deterministic contact sheet for human visual inspection."""

    paths = [Path(path) for path in images]
    if not paths:
        raise ValueError("Nenhuma página foi fornecida para a contact sheet.")
    gap = 22
    label_height = 28
    thumbnails: list[Image.Image] = []
    try:
        for path in paths:
            with Image.open(path) as source:
                image = source.convert("RGB")
                height = round(image.height * thumbnail_width / image.width)
                thumbnails.append(
                    image.resize((thumbnail_width, height), Image.Resampling.LANCZOS)
                )
        columns = max(1, min(columns, len(thumbnails)))
        rows = math.ceil(len(thumbnails) / columns)
        cell_height = max(image.height for image in thumbnails) + label_height
        sheet = Image.new(
            "RGB",
            (
                columns * thumbnail_width + (columns + 1) * gap,
                rows * cell_height + (rows + 1) * gap,
            ),
            "#E8E8EA",
        )
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default()
        for index, thumbnail in enumerate(thumbnails):
            row, column = divmod(index, columns)
            x = gap + column * (thumbnail_width + gap)
            y = gap + row * (cell_height + gap)
            draw.text((x, y + 6), f"Página {index + 1:02d}", fill="#16161C", font=font)
            sheet.paste(thumbnail, (x, y + label_height))
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(output, format="PNG", optimize=False)
        sheet.close()
        return output
    finally:
        for image in thumbnails:
            image.close()


def compare_with_golden(
    rendered_pages: Sequence[str | Path],
    golden_dir: str | Path,
    *,
    max_mae: float = GOLDEN_MAX_MAE,
    pixel_delta: int = GOLDEN_PIXEL_DELTA,
    max_changed_fraction: float = GOLDEN_MAX_CHANGED_FRACTION,
) -> dict[str, Any]:
    """Compare rendered pages with a golden using anti-aliasing-safe metrics.

    Thresholds use native 0..255 channel values.  Text extraction and geometry
    checks remain mandatory, so these tolerances only absorb rasterizer noise.
    """

    actual = [Path(path) for path in rendered_pages]
    golden_root = Path(golden_dir)
    expected = sorted(
        golden_root.glob("page-*.png"),
        key=lambda path: int(re.search(r"-(\d+)\.png$", path.name).group(1)),
    )
    issues: list[str] = []
    pages: list[dict[str, Any]] = []
    if len(actual) != len(expected):
        issues.append(
            f"Golden contém {len(expected)} páginas; render atual contém {len(actual)}."
        )
    for index, (actual_path, expected_path) in enumerate(zip(actual, expected), 1):
        with Image.open(actual_path) as actual_source, Image.open(expected_path) as expected_source:
            actual_image = actual_source.convert("RGB")
            expected_image = expected_source.convert("RGB")
            if actual_image.size != expected_image.size:
                issues.append(
                    f"Página {index}: dimensão {actual_image.size} difere do golden {expected_image.size}."
                )
                pages.append({"page": index, "dimensions_match": False})
                continue
            width, height = actual_image.size
            border = GOLDEN_BORDER_PX
            box = (border, border, width - border, height - border)
            actual_crop = actual_image.crop(box)
            expected_crop = expected_image.crop(box)
            difference = ImageChops.difference(actual_crop, expected_crop)
            stats = ImageStat.Stat(difference)
            mae = sum(stats.mean) / len(stats.mean)
            total = difference.width * difference.height
            red, green, blue = difference.split()
            maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
            threshold = maximum.point(lambda value: 255 if value > pixel_delta else 0)
            changed = threshold.histogram()[255]
            changed_fraction = changed / total if total else 0.0
            passed = mae <= max_mae and changed_fraction <= max_changed_fraction
            if not passed:
                issues.append(
                    f"Página {index}: regressão visual (MAE {mae:.3f}, "
                    f"pixels alterados {changed_fraction:.3%})."
                )
            pages.append(
                {
                    "page": index,
                    "dimensions_match": True,
                    "mae": round(mae, 6),
                    "changed_fraction": round(changed_fraction, 8),
                    "ok": passed,
                }
            )
    return {
        "ok": not issues,
        "issues": issues,
        "pages": pages,
        "thresholds": {
            "border_ignored_px": GOLDEN_BORDER_PX,
            "max_mae_0_255": max_mae,
            "pixel_delta_0_255": pixel_delta,
            "max_changed_fraction": max_changed_fraction,
        },
    }


__all__ = [
    "DEFAULT_RENDER_DPI",
    "PdfValidationDependencyError",
    "compare_with_golden",
    "create_contact_sheet",
    "inspect_pdf",
    "pdfium_version",
    "render_pdf",
]
