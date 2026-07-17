"""Embedded and inline image extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf

from ..config import ExtractionConfig
from ..geometry import BBox
from ..models import ImageElement
from ..native import safe_name, sha256_bytes


def _image_rects(page: pymupdf.Page, xref: int) -> list[tuple[pymupdf.Rect, pymupdf.Matrix | None]]:
    try:
        values = page.get_image_rects(xref, transform=True)
    except Exception:
        try:
            values = page.get_image_rects(xref)
        except Exception:
            return []
    result: list[tuple[pymupdf.Rect, pymupdf.Matrix | None]] = []
    for value in values:
        if isinstance(value, tuple) and len(value) == 2:
            result.append((pymupdf.Rect(value[0]), pymupdf.Matrix(value[1])))
        else:
            result.append((pymupdf.Rect(value), None))
    return result


def extract_images(
    doc: pymupdf.Document,
    page: pymupdf.Page,
    page_index: int,
    image_blocks: list[dict[str, Any]],
    assets_dir: Path,
    config: ExtractionConfig,
) -> list[ImageElement]:
    result: list[ImageElement] = []
    observed_boxes: list[BBox] = []
    seen_xrefs: set[int] = set()
    for raw_image in page.get_images(full=True):
        xref = int(raw_image[0])
        if xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)
        try:
            extracted = doc.extract_image(xref)
        except Exception:
            extracted = {}
        data = extracted.get("image")
        extension = str(extracted.get("ext") or "bin").lower()
        digest = sha256_bytes(data) if isinstance(data, bytes) else None
        asset_path: str | None = None
        if isinstance(data, bytes):
            target = assets_dir / f"xref_{xref}_{digest[:12] if digest else 'unknown'}.{safe_name(extension)}"
            if not target.exists():
                target.write_bytes(data)
            asset_path = f"assets/images/{target.name}"
        for occurrence, (rect, matrix) in enumerate(_image_rects(page, xref)):
            bbox = BBox.from_value(rect)
            if bbox.width < config.min_image_width or bbox.height < config.min_image_height:
                continue
            observed_boxes.append(bbox)
            result.append(
                ImageElement(
                    id=f"p{page_index + 1:04d}_image_x{xref}_{occurrence:03d}",
                    bbox=bbox,
                    xref=xref,
                    occurrence=occurrence,
                    pixel_width=int(extracted.get("width") or raw_image[2] or 0) or None,
                    pixel_height=int(extracted.get("height") or raw_image[3] or 0) or None,
                    colorspace=int(extracted.get("colorspace") or raw_image[4] or 0) or None,
                    bits_per_component=int(extracted.get("bpc") or raw_image[5] or 0) or None,
                    extension=extension,
                    asset_path=asset_path,
                    digest_sha256=digest,
                    transform=[float(value) for value in matrix] if matrix is not None else None,
                )
            )

    for index, block in enumerate(image_blocks):
        bbox = BBox.from_value(block.get("bbox", (0, 0, 0, 0)))
        if bbox.width < config.min_image_width or bbox.height < config.min_image_height:
            continue
        if any(bbox.overlap_ratio(existing, "min") >= 0.90 for existing in observed_boxes):
            continue
        data = block.get("image")
        if not isinstance(data, bytes):
            continue
        extension = str(block.get("ext") or "png").lower()
        digest = sha256_bytes(data)
        target = assets_dir / f"inline_p{page_index + 1:04d}_{index:03d}_{digest[:12]}.{safe_name(extension)}"
        if not target.exists():
            target.write_bytes(data)
        result.append(
            ImageElement(
                id=f"p{page_index + 1:04d}_image_inline_{index:03d}",
                bbox=bbox,
                xref=None,
                occurrence=0,
                pixel_width=int(block.get("width") or 0) or None,
                pixel_height=int(block.get("height") or 0) or None,
                colorspace=int(block.get("colorspace") or 0) or None,
                bits_per_component=int(block.get("bpc") or 0) or None,
                extension=extension,
                asset_path=f"assets/images/{target.name}",
                digest_sha256=digest,
                transform=[float(value) for value in block.get("transform", [])] or None,
                source="page.get_text(rawdict)",
            )
        )
    return result
