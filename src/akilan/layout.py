"""Deterministic geometry-first reading order reconstruction."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Literal

from .geometry import BBox
from .models import DrawingElement, ImageElement, ReadingOrderItem, TableElement, TextBlock

SpatialElement = TextBlock | TableElement | ImageElement | DrawingElement


@dataclass(frozen=True, slots=True)
class LayoutAnalysis:
    """Explainable page-layout evidence used by reading-order reconstruction."""

    column_boundaries: tuple[float, ...]
    column_count: int
    spanning_element_ids: tuple[str, ...]
    ambiguous_element_ids: tuple[str, ...]
    column_element_counts: tuple[int, ...]
    confidence: float = 1.0
    ambiguity_reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class _Candidate:
    element_type: Literal["text", "table", "image", "drawing"]
    element: SpatialElement
    column_index: int | None = None


def _infer_column_boundaries(boxes: list[BBox], page_width: float) -> list[float]:
    """Infer separators from persistent vertical whitespace between page elements."""

    usable = [box for box in boxes if 0 < box.width < page_width * 0.72]
    if len(usable) < 4:
        return []

    minimum_gap = page_width * 0.04
    edges = sorted({coordinate for box in usable for coordinate in (box.x0, box.x1)})
    candidates: list[tuple[int, float, float]] = []
    for left_edge, right_edge in pairwise(edges):
        gap_width = right_edge - left_edge
        if gap_width < minimum_gap:
            continue
        boundary = (left_edge + right_edge) / 2.0
        left_count = sum(box.x1 <= boundary for box in usable)
        right_count = sum(box.x0 >= boundary for box in usable)
        if left_count < 2 or right_count < 2:
            continue
        crossing_count = sum(box.x0 < boundary < box.x1 for box in usable)
        candidates.append((crossing_count, -gap_width, boundary))

    selected: list[float] = []
    for _, _, boundary in sorted(candidates):
        if all(abs(boundary - existing) >= page_width * 0.12 for existing in selected):
            selected.append(boundary)
        if len(selected) == 2:
            break
    return sorted(selected)


def _boundary_clearance(page_width: float) -> float:
    """Return the minimum evidence required on both sides of a separator."""

    return max(12.0, page_width * 0.03)


def _crosses_boundary(box: BBox, boundary: float, page_width: float) -> bool:
    """Return whether a box materially spans both sides of a column separator."""

    if not box.x0 < boundary < box.x1:
        return False
    clearance = _boundary_clearance(page_width)
    return boundary - box.x0 >= clearance and box.x1 - boundary >= clearance


def _near_boundary(box: BBox, boundary: float, page_width: float) -> bool:
    """Flag weak separator evidence so downstream evaluation can inspect it."""

    tolerance = _boundary_clearance(page_width)
    return min(abs(box.x0 - boundary), abs(box.x1 - boundary), abs(box.center[0] - boundary)) <= tolerance


def _column_index(box: BBox, boundaries: list[float], page_width: float) -> int | None:
    if not boundaries or box.width >= page_width * 0.72:
        return None
    if any(_crosses_boundary(box, boundary, page_width) for boundary in boundaries):
        return None
    center = box.center[0]
    return sum(center > boundary for boundary in boundaries)


def _layout_confidence(*, element_count: int, ambiguous_count: int, column_counts: list[int]) -> float:
    """Return a bounded, deterministic confidence score for inferred columns."""

    if element_count == 0:
        return 1.0
    ambiguity_penalty = ambiguous_count / element_count
    populated = [count for count in column_counts if count]
    imbalance_penalty = 0.0
    if len(populated) > 1:
        imbalance_penalty = (max(populated) - min(populated)) / element_count
    return round(max(0.0, min(1.0, 1.0 - ambiguity_penalty - 0.25 * imbalance_penalty)), 4)


def analyze_layout(*, page_width: float, elements: Sequence[SpatialElement]) -> LayoutAnalysis:
    """Return deterministic column, spanning, confidence, and ambiguity diagnostics."""

    boundaries = _infer_column_boundaries([element.bbox for element in elements], page_width)
    column_count = len(boundaries) + 1 if boundaries else 1
    spanning: list[str] = []
    ambiguous: list[str] = []
    counts = [0] * column_count

    for element in elements:
        column_index = _column_index(element.bbox, boundaries, page_width)
        if column_index is None:
            spanning.append(element.id)
        else:
            counts[column_index] += 1
            if any(_near_boundary(element.bbox, boundary, page_width) for boundary in boundaries):
                ambiguous.append(element.id)

    reasons: list[str] = []
    if ambiguous:
        reasons.append("elements_near_column_separator")
    populated = [count for count in counts if count]
    if len(populated) > 1 and max(populated) > 2 * min(populated):
        reasons.append("strong_column_population_imbalance")

    return LayoutAnalysis(
        column_boundaries=tuple(round(boundary, 4) for boundary in boundaries),
        column_count=column_count,
        spanning_element_ids=tuple(sorted(spanning)),
        ambiguous_element_ids=tuple(sorted(ambiguous)),
        column_element_counts=tuple(counts),
        confidence=_layout_confidence(
            element_count=len(elements),
            ambiguous_count=len(ambiguous),
            column_counts=counts,
        ),
        ambiguity_reasons=tuple(reasons),
    )


def _vertical_center(candidate: _Candidate) -> float:
    """Return a stable vertical anchor for mixed-layout band partitioning."""

    return candidate.element.bbox.center[1]


def _column_sort_key(candidate: _Candidate) -> tuple[int, float, float, str]:
    """Return a deterministic order key within one vertical layout band."""

    assert candidate.column_index is not None
    return (
        candidate.column_index,
        candidate.element.bbox.y0,
        candidate.element.bbox.x0,
        candidate.element.id,
    )


def build_reading_order(
    *,
    page_width: float,
    text_blocks: Sequence[TextBlock],
    tables: Sequence[TableElement],
    images: Sequence[ImageElement],
    drawings: Sequence[DrawingElement],
    suppress_table_text: bool,
) -> list[ReadingOrderItem]:
    """Interleave page elements using columns, vertical bands, and spanning objects."""

    candidates: list[_Candidate] = []
    table_boxes = [table.bbox for table in tables]
    for block in text_blocks:
        if suppress_table_text and any(block.bbox.overlap_ratio(table_box, "self") >= 0.55 for table_box in table_boxes):
            block.inside_table = True
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
        key=lambda item: (
            _vertical_center(item),
            item.element.bbox.y0,
            item.element.bbox.x0,
            item.element.id,
        ),
    )
    columnar = [candidate for candidate in candidates if candidate.column_index is not None]

    ordered: list[_Candidate] = []
    for span in spanning:
        span_center = _vertical_center(span)
        before = [item for item in columnar if _vertical_center(item) < span_center]
        before.sort(key=_column_sort_key)
        ordered.extend(before)
        if before:
            consumed = {id(item) for item in before}
            columnar = [item for item in columnar if id(item) not in consumed]
        ordered.append(span)

    columnar.sort(key=_column_sort_key)
    ordered.extend(columnar)

    result: list[ReadingOrderItem] = []
    for order, candidate in enumerate(ordered):
        candidate.element.reading_order = order
        if isinstance(candidate.element, TextBlock):
            candidate.element.column_index = candidate.column_index
        result.append(
            ReadingOrderItem(
                order=order,
                element_type=candidate.element_type,
                element_id=candidate.element.id,
                bbox=candidate.element.bbox,
                column_index=candidate.column_index,
            )
        )
    return result
