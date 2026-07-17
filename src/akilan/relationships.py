"""Deterministic cross-page section and caption relationship inference."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .geometry import BBox
from .models import PageArtifact, TextBlock

_HEADING_LEVELS = {
    "document_title": 0,
    "heading_1": 1,
    "heading_2": 2,
    "heading_3": 3,
}
_CONTENT_ROLES = {"paragraph", "list_item", "caption", "code", "footnote"}
_OWNED_RELATIONSHIPS = {"parent_heading", "section_heading", "contains", "describes"}


@dataclass(frozen=True, slots=True)
class _VisualCandidate:
    element_id: str
    bbox: BBox
    kind_rank: int


def _ordered_text_blocks(page: PageArtifact) -> list[TextBlock]:
    order_by_id = {
        item.element_id: item.order
        for item in page.reading_order
        if item.element_type == "text"
    }
    return sorted(
        page.text_blocks,
        key=lambda block: (
            order_by_id.get(block.id, 10**9),
            block.bbox.y0,
            block.bbox.x0,
            block.id,
        ),
    )


def _reset_owned_relationships(blocks: Iterable[TextBlock]) -> None:
    for block in blocks:
        for relationship in _OWNED_RELATIONSHIPS:
            block.relationships.pop(relationship, None)


def _append_relationship(block: TextBlock, name: str, element_id: str) -> None:
    values = block.relationships.setdefault(name, [])
    if element_id not in values:
        values.append(element_id)


def _horizontal_overlap_ratio(left: BBox, right: BBox) -> float:
    overlap = max(0.0, min(left.x1, right.x1) - max(left.x0, right.x0))
    denominator = min(left.width, right.width) or 1.0
    return overlap / denominator


def _vertical_gap(left: BBox, right: BBox) -> float:
    if left.y1 < right.y0:
        return right.y0 - left.y1
    if right.y1 < left.y0:
        return left.y0 - right.y1
    return 0.0


def _visual_candidates(page: PageArtifact) -> list[_VisualCandidate]:
    candidates = [
        *(_VisualCandidate(table.id, table.bbox, 0) for table in page.tables),
        *(_VisualCandidate(image.id, image.bbox, 1) for image in page.images),
        *(_VisualCandidate(drawing.id, drawing.bbox, 2) for drawing in page.drawings),
    ]
    return sorted(candidates, key=lambda item: (item.kind_rank, item.bbox.y0, item.bbox.x0, item.element_id))


def _link_caption(page: PageArtifact, caption: TextBlock) -> None:
    maximum_gap = max(24.0, page.height * 0.12)
    ranked: list[tuple[float, float, int, str]] = []
    for candidate in _visual_candidates(page):
        gap = _vertical_gap(caption.bbox, candidate.bbox)
        overlap = _horizontal_overlap_ratio(caption.bbox, candidate.bbox)
        if gap > maximum_gap or overlap < 0.15:
            continue
        ranked.append((gap, -overlap, candidate.kind_rank, candidate.element_id))
    if ranked:
        _append_relationship(caption, "describes", min(ranked)[3])


def infer_document_relationships(pages: list[PageArtifact]) -> None:
    """Populate auditable relationships without changing source evidence.

    The function is deterministic and idempotent. Heading state intentionally spans
    page boundaries, allowing body content on a new page to remain attached to the
    most recent section heading. Ambiguous caption associations are resolved only
    when a nearby visual element has meaningful horizontal overlap.
    """

    all_blocks = [block for page in pages for block in page.text_blocks]
    _reset_owned_relationships(all_blocks)

    heading_stack: list[tuple[int, TextBlock]] = []
    for page in sorted(pages, key=lambda item: (item.page_index, item.page_number)):
        for block in _ordered_text_blocks(page):
            level = _HEADING_LEVELS.get(block.semantic_role)
            if level is not None:
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                if heading_stack:
                    parent = heading_stack[-1][1]
                    _append_relationship(block, "parent_heading", parent.id)
                    _append_relationship(parent, "contains", block.id)
                heading_stack.append((level, block))
                continue

            if block.semantic_role in _CONTENT_ROLES and heading_stack:
                heading = heading_stack[-1][1]
                _append_relationship(block, "section_heading", heading.id)
                _append_relationship(heading, "contains", block.id)

            if block.semantic_role == "caption":
                _link_caption(page, block)

    for block in all_blocks:
        for values in block.relationships.values():
            values.sort()
