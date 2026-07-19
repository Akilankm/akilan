"""Deterministic, audit-first cross-page table continuation inference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import PageArtifact, TableElement

_METRIC = "table_continuations"
_RULE_ID = "adjacent-page-table-continuation-v1"


@dataclass(frozen=True, slots=True)
class _Candidate:
    previous: TableElement
    current: TableElement
    confidence: float
    header_match: float
    width_match: float

    @property
    def sort_key(self) -> tuple[float, str, str]:
        return (-self.confidence, self.previous.id, self.current.id)


def _normalized_row(row: list[str | None]) -> tuple[str, ...]:
    return tuple(" ".join((value or "").casefold().split()) for value in row)


def _header_similarity(left: TableElement, right: TableElement) -> float:
    if not left.rows or not right.rows:
        return 0.0
    left_header = _normalized_row(left.rows[0])
    right_header = _normalized_row(right.rows[0])
    if not left_header or not right_header or len(left_header) != len(right_header):
        return 0.0
    matches = sum(a == b and bool(a) for a, b in zip(left_header, right_header, strict=True))
    return matches / len(left_header)


def _width_similarity(left: TableElement, right: TableElement) -> float:
    denominator = max(left.bbox.width, right.bbox.width, 1.0)
    return 1.0 - min(1.0, abs(left.bbox.width - right.bbox.width) / denominator)


def _candidate(previous_page: PageArtifact, current_page: PageArtifact, left: TableElement, right: TableElement) -> _Candidate | None:
    if left.column_count <= 0 or left.column_count != right.column_count:
        return None
    if left.bbox.y1 < previous_page.height * 0.72:
        return None
    if right.bbox.y0 > current_page.height * 0.28:
        return None

    header_match = _header_similarity(left, right)
    width_match = _width_similarity(left, right)
    x_alignment = 1.0 - min(1.0, abs(left.bbox.x0 - right.bbox.x0) / max(previous_page.width, current_page.width, 1.0))
    confidence = 0.45 + (0.25 * header_match) + (0.20 * width_match) + (0.10 * x_alignment)
    if header_match == 0.0 and width_match < 0.85:
        return None
    return _Candidate(left, right, confidence, header_match, width_match)


def infer_table_continuations(pages: list[PageArtifact]) -> None:
    """Record non-destructive continuation evidence in page metrics.

    Native table detections remain unchanged. Evidence is regenerated idempotently,
    considers adjacent pages only, and abstains when the best candidate is ambiguous.
    """

    ordered = sorted(pages, key=lambda page: (page.page_index, page.page_number))
    for page in ordered:
        page.metrics.pop(_METRIC, None)

    for previous_page, current_page in zip(ordered, ordered[1:], strict=False):
        if current_page.page_number != previous_page.page_number + 1:
            continue
        candidates = sorted(
            (
                candidate
                for left in previous_page.tables
                for right in current_page.tables
                if (candidate := _candidate(previous_page, current_page, left, right)) is not None
            ),
            key=lambda item: item.sort_key,
        )
        if not candidates:
            continue
        best = candidates[0]
        if len(candidates) > 1 and best.confidence - candidates[1].confidence < 0.08:
            continue
        evidence: dict[str, Any] = {
            "source_table_id": best.previous.id,
            "target_table_id": best.current.id,
            "relationship": "continues_on_next_page",
            "rule_id": _RULE_ID,
            "confidence": round(min(1.0, max(0.0, best.confidence)), 4),
            "signals": {
                "column_count_match": True,
                "header_similarity": round(best.header_match, 4),
                "width_similarity": round(best.width_match, 4),
            },
        }
        previous_page.metrics[_METRIC] = [evidence]
        current_page.metrics[_METRIC] = [
            {
                **evidence,
                "relationship": "continues_from_previous_page",
            }
        ]
