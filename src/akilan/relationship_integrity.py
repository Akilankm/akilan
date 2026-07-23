"""Read-only integrity checks for inferred artifact relationships."""

from __future__ import annotations

from dataclasses import dataclass

from .models import PageArtifact

_ELEMENT_COLLECTIONS = (
    "text_blocks",
    "tables",
    "images",
    "drawings",
    "links",
    "annotations",
    "widgets",
)


@dataclass(frozen=True, slots=True)
class RelationshipIntegrityViolation:
    """One deterministic relationship-graph integrity violation."""

    page_index: int
    source_id: str
    relationship: str
    target_id: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        """Return stable machine-readable validation evidence."""

        return {
            "page_index": self.page_index,
            "source_id": self.source_id,
            "relationship": self.relationship,
            "target_id": self.target_id,
            "reason": self.reason,
            "rule_id": "relationship-target-integrity-v1",
        }


def find_relationship_integrity_violations(
    pages: list[PageArtifact],
) -> list[RelationshipIntegrityViolation]:
    """Return malformed, duplicate, self, and dangling relationship targets.

    The validator is intentionally read-only and document-scoped because valid
    relationships may cross page boundaries. Results are independent of page,
    element, relationship-key, and target input order.
    """

    known_ids = _collect_element_ids(pages)
    violations: list[RelationshipIntegrityViolation] = []

    for page in sorted(pages, key=lambda item: (item.page_index, item.page_number)):
        for source in sorted(page.text_blocks, key=lambda item: item.id):
            for relationship, targets in sorted(source.relationships.items()):
                normalized_relationship = relationship.strip()
                if not normalized_relationship:
                    violations.append(
                        RelationshipIntegrityViolation(
                            page_index=page.page_index,
                            source_id=source.id,
                            relationship=relationship,
                            target_id="",
                            reason="relationship name must be non-empty",
                        )
                    )
                    continue

                observed_targets: set[str] = set()
                for target_id in sorted(targets):
                    if not target_id:
                        reason = "target ID must be non-empty"
                    elif target_id == source.id:
                        reason = "self-referential relationship is not allowed"
                    elif target_id in observed_targets:
                        reason = "duplicate relationship target"
                    elif target_id not in known_ids:
                        reason = "target ID does not exist in the document artifact"
                    else:
                        observed_targets.add(target_id)
                        continue

                    violations.append(
                        RelationshipIntegrityViolation(
                            page_index=page.page_index,
                            source_id=source.id,
                            relationship=normalized_relationship,
                            target_id=target_id,
                            reason=reason,
                        )
                    )
                    observed_targets.add(target_id)

    return sorted(
        violations,
        key=lambda item: (
            item.page_index,
            item.source_id,
            item.relationship,
            item.target_id,
            item.reason,
        ),
    )


def _collect_element_ids(pages: list[PageArtifact]) -> set[str]:
    known_ids: set[str] = set()
    for page in pages:
        for collection in _ELEMENT_COLLECTIONS:
            known_ids.update(
                element.id
                for element in getattr(page, collection)
                if isinstance(element.id, str) and element.id
            )
    return known_ids
