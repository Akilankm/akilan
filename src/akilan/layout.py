"""Deterministic geometry-first reading order reconstruction."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Protocol

from .geometry import BBox
from .models import ReadingOrderItem


class SpatialElement(Protocol):
    id: str
    bbox: BBox
    reading_order: int | None


@dataclass(slots=True)
class _Candidate:
    element_type: str
    element: SpatialElement
    column_index: int | None = None


def _infer_column_boundaries(boxes: list[BBox], page_width: float) -> list[float]:
    """Infer likely column separators from stable x-center gaps."""

    usable = [box for box in boxes if 0 < box.width < page_width * 0.72]
    if len(usable) < 4:
        return []
    centers = sorted(box.center[0] for box in usable)
    gaps = [(centers[index + 1] - centers[index], index) for index in range(len(centers) - 1)]
    meaningful = [(gap, index) for gap, index in gaps if gap >= page_width * 0.12]
    if not meaningful:
        return []
    typical_width = median(box.width for box in usable)
    selected = sorted(meaningful, reverse=True)[:2]
    boundaries = sorted((centers[index] + centers[index + 1]) / 2 for gap, index in selected if gap > typical_width * 0.45)
    return boundaries


def _column_index(box: BBox, boundaries: list[float], page_width: float) -> int | None:
    if not boundaries or box.width >= page_width * 0.72:
        return None
    center = box.center[0]
    return sum(center > boundary for boundary in boundaries)


def build_reading_order(
    *,
    page_width: float,
    text_blocks: list[SpatialElement],
    tables: list[SpatialElement],
    images: list[SpatialElement],
    drawings: list[SpatialElement],
    suppress_table_text: bool,
) -> list[ReadingOrderItem]:
    """Interleave page elements using columns, vertical bands, and spanning objects."""

    candidates: list[_Candidate] = []
    table_boxes = [table.bbox for table in tables]
    for block in text_blocks:
        if suppress_table_text and any(block.bbox.overlap_ratio(table_box, "self") >= 0.55 for table_box in table_boxes):
            setattr(block, "inside_table", True)
            continue
        candidates.append(_Candidate("text", block))
    candidates.extend(_Candidate("table", table) for table in tables)
    candidates.extend(_Candidate("image", image) for image in images)

    # Drawings are preserved in the artifact, but only material drawings are part
    # of reading order. Thin rules and decoration otherwise dominate the sequence.
    candidates.extend(
        _Candidate("drawing", drawing)
        for drawing in drawings
        if drawing.bbox.area >= max(36.0, page_width * 0.2)
    )

    boundaries = _infer_column_boundaries([candidate.element.bbox for candidate in candidates], page_width)
    for candidate in candidates:
        candidate.column_index = _column_index(candidate.element.bbox, boundaries, page_width)

    spanning = sorted(
        [candidate for candidate in candidates if candidate.column_index is None],
        key=lambda item: (item.element.bbox.y0, item.element.bbox.x0),
    )
    columnar = [candidate for candidate in candidates if candidate.column_index is not None]

    ordered: list[_Candidate] = []
    cursor_y = float("-inf")
    for span in spanning:
        before = [
            item
            for item in columnar
            if cursor_y <= item.element.bbox.y0 < span.element.bbox.y0
        ]
        before.sort(key=lambda item: (item.column_index or 0, item.element.bbox.y0, item.element.bbox.x0))
        ordered.extend(before)
        columnar = [item for item in columnar if item not in before]
        ordered.append(span)
        cursor_y = max(cursor_y, span.element.bbox.y1)

    columnar.sort(key=lambda item: (item.column_index or 0, item.element.bbox.y0, item.element.bbox.x0))
    ordered.extend(columnar)

    result: list[ReadingOrderItem] = []
    for order, candidate in enumerate(ordered):
        candidate.element.reading_order = order
        if hasattr(candidate.element, "column_index"):
            setattr(candidate.element, "column_index", candidate.column_index)
        result.append(
            ReadingOrderItem(
                order=order,
                element_type=candidate.element_type,  # type: ignore[arg-type]
                element_id=candidate.element.id,
                bbox=candidate.element.bbox,
                column_index=candidate.column_index,
            )
        )
    return result
