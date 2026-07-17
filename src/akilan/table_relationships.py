"""Deterministic cross-page table continuation inference."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import PageArtifact, TableElement

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class TableContinuation:
    """Auditable relationship between adjacent-page table fragments."""

    source_table_id: str
    target_table_id: str
    group_id: str
    confidence: float
    repeated_header: bool
    column_count: int
    rule_id: str = "adjacent-page-table-continuation-v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "source_table_id": self.source_table_id,
            "target_table_id": self.target_table_id,
            "group_id": self.group_id,
            "confidence": self.confidence,
            "repeated_header": self.repeated_header,
            "column_count": self.column_count,
            "rule_id": self.rule_id,
        }


def _normalize_cell(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(_TOKEN_PATTERN.findall(value.casefold()))


def _header(table: TableElement) -> tuple[str, ...]:
    if not table.rows:
        return ()
    return tuple(_normalize_cell(value) for value in table.rows[0])


def _near_bottom(page: PageArtifact, table: TableElement) -> bool:
    return table.bbox.y1 >= page.height * 0.78


def _near_top(page: PageArtifact, table: TableElement) -> bool:
    return table.bbox.y0 <= page.height * 0.22


def _horizontal_alignment(left: TableElement, right: TableElement) -> float:
    overlap = max(0.0, min(left.bbox.x1, right.bbox.x1) - max(left.bbox.x0, right.bbox.x0))
    denominator = max(left.bbox.width, right.bbox.width, 1.0)
    return overlap / denominator


def _candidate_score(left: TableElement, right: TableElement) -> tuple[float, bool] | None:
    if left.column_count <= 0 or left.column_count != right.column_count:
        return None
    alignment = _horizontal_alignment(left, right)
    if alignment < 0.72:
        return None

    left_header = _header(left)
    right_header = _header(right)
    repeated_header = bool(left_header and left_header == right_header and any(left_header))
    confidence = 0.72 + min(0.16, alignment * 0.16)
    if repeated_header:
        confidence += 0.12
    return min(round(confidence, 4), 0.99), repeated_header


def infer_table_continuations(pages: list[PageArtifact]) -> list[TableContinuation]:
    """Infer conservative continuation edges between adjacent pages.

    Native PyMuPDF table detections remain untouched. Results are written into
    each page's additive ``metrics["table_continuations"]`` projection and also
    returned for direct testing or downstream processing.
    """

    ordered_pages = sorted(pages, key=lambda page: (page.page_index, page.page_number))
    for page in ordered_pages:
        page.metrics.pop("table_continuations", None)

    relationships: list[TableContinuation] = []
    for left_page, right_page in zip(ordered_pages, ordered_pages[1:], strict=False):
        if right_page.page_index != left_page.page_index + 1:
            continue
        left_tables = sorted(left_page.tables, key=lambda table: (table.bbox.y0, table.bbox.x0, table.id))
        right_tables = sorted(right_page.tables, key=lambda table: (table.bbox.y0, table.bbox.x0, table.id))
        candidates: list[tuple[float, str, str, bool, TableElement, TableElement]] = []
        for left in left_tables:
            if not _near_bottom(left_page, left):
                continue
            for right in right_tables:
                if not _near_top(right_page, right):
                    continue
                scored = _candidate_score(left, right)
                if scored is None:
                    continue
                confidence, repeated_header = scored
                candidates.append((-confidence, left.id, right.id, repeated_header, left, right))

        used_left: set[str] = set()
        used_right: set[str] = set()
        for negative_confidence, _, _, repeated_header, left, right in sorted(candidates):
            if left.id in used_left or right.id in used_right:
                continue
            confidence = -negative_confidence
            relationship = TableContinuation(
                source_table_id=left.id,
                target_table_id=right.id,
                group_id=f"table_group_{left.id}_{right.id}",
                confidence=confidence,
                repeated_header=repeated_header,
                column_count=left.column_count,
            )
            relationships.append(relationship)
            used_left.add(left.id)
            used_right.add(right.id)

    by_page: dict[int, list[dict[str, object]]] = {}
    table_page = {table.id: page.page_index for page in ordered_pages for table in page.tables}
    for relationship in relationships:
        payload = relationship.to_dict()
        for page_index in {
            table_page[relationship.source_table_id],
            table_page[relationship.target_table_id],
        }:
            by_page.setdefault(page_index, []).append(payload)

    for page in ordered_pages:
        if page.page_index in by_page:
            page.metrics["table_continuations"] = sorted(
                by_page[page.page_index],
                key=lambda item: (str(item["source_table_id"]), str(item["target_table_id"])),
            )
    return relationships
