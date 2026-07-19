"""Deterministic validation for relationship inference inputs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import PageArtifact

_FOOTNOTE_DEFINITION_PATTERN = re.compile(
    r"^\s*(\[(?:\d{1,3}|[a-z])\])\s+\S",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class DuplicateFootnoteMarker:
    """A page-local footnote marker assigned to multiple definitions."""

    page_index: int
    marker: str
    definition_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return deterministic machine-readable evidence."""

        return {
            "page_index": self.page_index,
            "marker": self.marker,
            "definition_ids": list(self.definition_ids),
            "rule_id": "duplicate-footnote-definition-marker-v1",
        }


def find_duplicate_footnote_markers(
    pages: list[PageArtifact],
) -> list[DuplicateFootnoteMarker]:
    """Return duplicate explicit footnote markers without mutating artifacts.

    Only text blocks already classified as ``footnote`` and beginning with the
    supported bracketed marker contract are considered. Results are stable
    across page and block input order.
    """

    conflicts: list[DuplicateFootnoteMarker] = []
    for page in sorted(pages, key=lambda item: (item.page_index, item.page_number)):
        definitions_by_marker: dict[str, list[str]] = {}
        for block in page.text_blocks:
            if block.semantic_role != "footnote":
                continue
            match = _FOOTNOTE_DEFINITION_PATTERN.match(block.text)
            if match is None:
                continue
            marker = match.group(1).lower()
            definitions_by_marker.setdefault(marker, []).append(block.id)

        for marker, definition_ids in sorted(definitions_by_marker.items()):
            unique_ids = tuple(sorted(set(definition_ids)))
            if len(unique_ids) > 1:
                conflicts.append(
                    DuplicateFootnoteMarker(
                        page_index=page.page_index,
                        marker=marker,
                        definition_ids=unique_ids,
                    )
                )
    return conflicts
