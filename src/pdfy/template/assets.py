"""Packaged image access that also works from zipped distributions."""

from io import BytesIO

from reportlab.lib.utils import ImageReader

from pdfy.design.typography import asset_bytes


def image_asset(folder: str, filename: str) -> ImageReader:
    return ImageReader(BytesIO(asset_bytes(folder, filename)))
