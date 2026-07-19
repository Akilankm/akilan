"""Deterministic cross-page section, caption, and footnote relationship inference."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .geometry import BBox
from .models import PageArtifact, TextBlock

_HEADING_LEVELS = {
    "document_title": 0,
    "heading_1": 1,
    "heading_2": 2,
    "heading_3": 3,
}
_CONTENT_ROLES = {"paragraph", "list_item", "caption", "code", "footnote"}
_FOOTNOTE_SOURCE_ROLES = {"paragraph", "list_item", "caption", "code"}
_OWNED_RELATIONSHIPS = {
    "parent_heading",
    "section_heading",
    "contains",
    "describes",
    "footnote_reference",
    "has_footnote",
}
_EVIDENCE_METRIC = "relationship_evidence"
_AMBIGUITY_METRIC = "relationship_ambiguities"
_RULE_PARENT_HEADING = "heading-stack-parent-v1"
_RULE_SECTION_HEADING = "active-section-membership-v1"
_RULE_CONTAINS = "direct-section-containment-v1"
_RULE_CAPTION_DESCRIBES = "caption-proximity-overlap-v2"
_RULE_CAPTION_AMBIGUITY = "caption-candidate-margin-v1"
_RULE_CAPTION_TYPE_ABSTENTION = "caption-explicit-type-gate-v1"
_RULE_FOOTNOTE_REFERENCE = "explicit-bracketed-footnote-marker-v1"
_MINIMUM_CAPTION_MARGIN = 0.08
_TABLE_CAPTION_PATTERN = re.compile(r"^\s*(?:table|tab\.)\s*(?:\d+|[ivxlcdm]+)?\b", re.IGNORECASE)
_FIGURE_CAPTION_PATTERN = re.compile(
    r"^\s*(?:figure|fig\.)\s*(?:\d+|[ivxlcdm]+)?\b", re.IGNORECASE
)
_FOOTNOTE_DEFINITION_PATTERN = re.compile(r"^\s*(\[(?:\d{1,3}|[a-z])\])\s+\S", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class _VisualCandidate:
    element_id: str
    bbox: BBox
    kind_rank: int


@dataclass(frozen=True, slots=True)
class _RankedCaptionCandidate:
    element_id: str
    kind_rank: int
    gap: float
    overlap: float
    confidence: float

    @property
    def sort_key(self) -> tuple[float, float, float, int, str]:
        """Prefer stronger evidence before deterministic geometric tie-breakers."""

        return (-self.confidence, self.gap, -self.overlap, self.kind_rank, self.element_id)


@dataclass(frozen=True, slots=True)
class _RelationshipEvidence:
    source_id: str
    target_id: str
    relationship: str
    rule_id: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "rule_id": self.rule_id,
            "confidence": round(max(0.0, min(1.0, self.confidence)), 4),
        }


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


def _reset_relationship_evidence(pages: Iterable[PageArtifact]) -> None:
    for page in pages:
        page.metrics.pop(_EVIDENCE_METRIC, None)
        page.metrics.pop(_AMBIGUITY_METRIC, None)


def _append_relationship(block: TextBlock, name: str, element_id: str) -> None:
    values = block.relationships.setdefault(name, [])
    if element_id not in values:
        values.append(element_id)


def _append_evidence(
    evidence_by_page: dict[int, list[_RelationshipEvidence]],
    page_index: int,
    *,
    source_id: str,
    target_id: str,
    relationship: str,
    rule_id: str,
    confidence: float,
) -> None:
    evidence = _RelationshipEvidence(
        source_id=source_id,
        target_id=target_id,
        relationship=relationship,
        rule_id=rule_id,
        confidence=confidence,
    )
    if evidence not in evidence_by_page[page_index]:
        evidence_by_page[page_index].append(evidence)


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
    return sorted(
        candidates,
        key=lambda item: (item.kind_rank, item.bbox.y0, item.bbox.x0, item.element_id),
    )


def _explicit_caption_kind_ranks(text: str) -> tuple[str, frozenset[int]] | None:
    """Return an explicit caption label and compatible visual-kind ranks."""

    if _TABLE_CAPTION_PATTERN.match(text):
        return ("table", frozenset({0}))
    if _FIGURE_CAPTION_PATTERN.match(text):
        return ("figure", frozenset({1, 2}))
    return None


def _eligible_caption_candidates(
    page: PageArtifact,
    caption: TextBlock,
) -> list[_RankedCaptionCandidate]:
    maximum_gap = max(24.0, page.height * 0.12)
    ranked: list[_RankedCaptionCandidate] = []
    for candidate in _visual_candidates(page):
        gap = _vertical_gap(caption.bbox, candidate.bbox)
        overlap = _horizontal_overlap_ratio(caption.bbox, candidate.bbox)
        if gap > maximum_gap or overlap < 0.15:
            continue
        distance_score = 1.0 - min(1.0, gap / maximum_gap)
        confidence = 0.55 + (0.25 * overlap) + (0.20 * distance_score)
        ranked.append(
            _RankedCaptionCandidate(
                element_id=candidate.element_id,
                kind_rank=candidate.kind_rank,
                gap=gap,
                overlap=overlap,
                confidence=confidence,
            )
        )
    return sorted(ranked, key=lambda item: item.sort_key)


def _rank_caption_candidates(
    page: PageArtifact,
    caption: TextBlock,
) -> tuple[list[_RankedCaptionCandidate], dict[str, Any] | None]:
    ranked = _eligible_caption_candidates(page, caption)
    explicit_kind = _explicit_caption_kind_ranks(caption.text)
    if explicit_kind is None:
        return ranked, None

    label, compatible_ranks = explicit_kind
    compatible = [candidate for candidate in ranked if candidate.kind_rank in compatible_ranks]
    if compatible:
        return compatible, None
    if not ranked:
        return [], None
    return [], {
        "source_id": caption.id,
        "relationship": "describes",
        "rule_id": _RULE_CAPTION_TYPE_ABSTENTION,
        "candidate_ids": sorted(candidate.element_id for candidate in ranked),
        "expected_visual_type": label,
    }


def _link_caption(
    page: PageArtifact,
    caption: TextBlock,
    evidence_by_page: dict[int, list[_RelationshipEvidence]],
    ambiguity_by_page: dict[int, list[dict[str, Any]]],
) -> None:
    ranked, type_abstention = _rank_caption_candidates(page, caption)
    if type_abstention is not None:
        ambiguity_by_page[page.page_index].append(type_abstention)
        return
    if not ranked:
        return

    best = ranked[0]
    if len(ranked) > 1:
        runner_up = ranked[1]
        confidence_margin = best.confidence - runner_up.confidence
        if confidence_margin < _MINIMUM_CAPTION_MARGIN:
            ambiguity_by_page[page.page_index].append(
                {
                    "source_id": caption.id,
                    "relationship": "describes",
                    "rule_id": _RULE_CAPTION_AMBIGUITY,
                    "candidate_ids": sorted([best.element_id, runner_up.element_id]),
                    "confidence_margin": round(confidence_margin, 4),
                    "minimum_margin": _MINIMUM_CAPTION_MARGIN,
                }
            )
            return

    _append_relationship(caption, "describes", best.element_id)
    _append_evidence(
        evidence_by_page,
        page.page_index,
        source_id=caption.id,
        target_id=best.element_id,
        relationship="describes",
        rule_id=_RULE_CAPTION_DESCRIBES,
        confidence=best.confidence,
    )


def _link_explicit_footnotes(
    page: PageArtifact,
    evidence_by_page: dict[int, list[_RelationshipEvidence]],
) -> None:
    """Link exact bracketed footnote markers to preceding same-page content.

    The rule is deliberately narrow: only blocks classified as ``footnote`` whose
    text starts with ``[1]``-style or ``[a]``-style markers are considered. A source
    must contain that exact marker as a standalone token and precede the definition
    in reading order. Multiple explicit references are retained rather than guessed
    into a single source.
    """

    ordered = _ordered_text_blocks(page)
    order_by_id = {block.id: index for index, block in enumerate(ordered)}
    for footnote in ordered:
        if footnote.semantic_role != "footnote":
            continue
        marker_match = _FOOTNOTE_DEFINITION_PATTERN.match(footnote.text)
        if marker_match is None:
            continue
        marker = marker_match.group(1)
        marker_pattern = re.compile(rf"(?<!\w){re.escape(marker)}(?!\w)", re.IGNORECASE)
        references = [
            block
            for block in ordered
            if block.semantic_role in _FOOTNOTE_SOURCE_ROLES
            and order_by_id[block.id] < order_by_id[footnote.id]
            and marker_pattern.search(block.text)
        ]
        for source in references:
            confidence = 0.95 * min(source.semantic_confidence, footnote.semantic_confidence)
            _append_relationship(footnote, "footnote_reference", source.id)
            _append_relationship(source, "has_footnote", footnote.id)
            _append_evidence(
                evidence_by_page,
                page.page_index,
                source_id=footnote.id,
                target_id=source.id,
                relationship="footnote_reference",
                rule_id=_RULE_FOOTNOTE_REFERENCE,
                confidence=confidence,
            )
            _append_evidence(
                evidence_by_page,
                page.page_index,
                source_id=source.id,
                target_id=footnote.id,
                relationship="has_footnote",
                rule_id=_RULE_FOOTNOTE_REFERENCE,
                confidence=confidence,
            )


def infer_document_relationships(pages: list[PageArtifact]) -> None:
    """Populate deterministic relationships and page-local audit evidence.

    Existing relationship lists remain the compatibility projection. Each inferred
    edge is additionally recorded under ``page.metrics.relationship_evidence`` with
    a stable rule identifier and bounded confidence. Evidence is owned by this pass,
    regenerated idempotently, and stored on the source element's page.
    """

    ordered_pages = sorted(pages, key=lambda item: (item.page_index, item.page_number))
    all_blocks = [block for page in ordered_pages for block in page.text_blocks]
    block_page = {
        block.id: page.page_index
        for page in ordered_pages
        for block in page.text_blocks
    }
    evidence_by_page: dict[int, list[_RelationshipEvidence]] = {
        page.page_index: [] for page in ordered_pages
    }
    ambiguity_by_page: dict[int, list[dict[str, Any]]] = {
        page.page_index: [] for page in ordered_pages
    }
    _reset_owned_relationships(all_blocks)
    _reset_relationship_evidence(ordered_pages)

    heading_stack: list[tuple[int, TextBlock]] = []
    for page in ordered_pages:
        for block in _ordered_text_blocks(page):
            level = _HEADING_LEVELS.get(block.semantic_role)
            if level is not None:
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                if heading_stack:
                    parent = heading_stack[-1][1]
                    confidence = min(block.semantic_confidence, parent.semantic_confidence)
                    _append_relationship(block, "parent_heading", parent.id)
                    _append_relationship(parent, "contains", block.id)
                    _append_evidence(
                        evidence_by_page,
                        page.page_index,
                        source_id=block.id,
                        target_id=parent.id,
                        relationship="parent_heading",
                        rule_id=_RULE_PARENT_HEADING,
                        confidence=confidence,
                    )
                    _append_evidence(
                        evidence_by_page,
                        block_page[parent.id],
                        source_id=parent.id,
                        target_id=block.id,
                        relationship="contains",
                        rule_id=_RULE_CONTAINS,
                        confidence=confidence,
                    )
                heading_stack.append((level, block))
                continue

            if block.semantic_role in _CONTENT_ROLES and heading_stack:
                heading = heading_stack[-1][1]
                confidence = min(block.semantic_confidence, heading.semantic_confidence)
                _append_relationship(block, "section_heading", heading.id)
                _append_relationship(heading, "contains", block.id)
                _append_evidence(
                    evidence_by_page,
                    page.page_index,
                    source_id=block.id,
                    target_id=heading.id,
                    relationship="section_heading",
                    rule_id=_RULE_SECTION_HEADING,
                    confidence=confidence,
                )
                _append_evidence(
                    evidence_by_page,
                    block_page[heading.id],
                    source_id=heading.id,
                    target_id=block.id,
                    relationship="contains",
                    rule_id=_RULE_CONTAINS,
                    confidence=confidence,
                )

            if block.semantic_role == "caption":
                _link_caption(page, block, evidence_by_page, ambiguity_by_page)

        _link_explicit_footnotes(page, evidence_by_page)

    for block in all_blocks:
        for relationship in _OWNED_RELATIONSHIPS:
            if relationship in block.relationships:
                block.relationships[relationship].sort()

    for page in ordered_pages:
        evidence = sorted(
            evidence_by_page[page.page_index],
            key=lambda item: (
                item.source_id,
                item.relationship,
                item.target_id,
                item.rule_id,
            ),
        )
        if evidence:
            page.metrics[_EVIDENCE_METRIC] = [item.to_dict() for item in evidence]
        ambiguities = sorted(
            ambiguity_by_page[page.page_index],
            key=lambda item: (item["source_id"], item["relationship"], item["candidate_ids"]),
        )
        if ambiguities:
            page.metrics[_AMBIGUITY_METRIC] = ambiguities
