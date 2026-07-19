"""Read-only validation for document-wide artifact element identities."""

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


@dataclass(frozen=True, slots=True, order=True)
class ElementIdentityOccurrence:
    """One stable location where an artifact element ID is defined."""

    page_index: int
    collection: str

    def to_dict(self) -> dict[str, object]:
        """Return deterministic machine-readable location evidence."""

        return {
            "page_index": self.page_index,
            "collection": self.collection,
        }


@dataclass(frozen=True, slots=True)
class DuplicateElementIdentity:
    """One element ID defined by more than one artifact element."""

    element_id: str
    occurrences: tuple[ElementIdentityOccurrence, ...]

    def to_dict(self) -> dict[str, object]:
        """Return stable machine-readable validation evidence."""

        return {
            "element_id": self.element_id,
            "occurrences": [item.to_dict() for item in self.occurrences],
            "rule_id": "document-element-id-uniqueness-v1",
        }


def find_duplicate_element_ids(
    pages: list[PageArtifact],
) -> list[DuplicateElementIdentity]:
    """Return blank and duplicate document-wide artifact element identities.

    Relationship edges address elements by ID across the complete document, so
    every non-empty ID must resolve to exactly one element. Results are
    independent of page and collection input order and the source artifact is
    never mutated.
    """

    occurrences_by_id: dict[str, list[ElementIdentityOccurrence]] = {}
    for page in sorted(pages, key=lambda item: (item.page_index, item.page_number)):
        for collection in _ELEMENT_COLLECTIONS:
            for element in getattr(page, collection):
                element_id = element.id if isinstance(element.id, str) else ""
                occurrences_by_id.setdefault(element_id, []).append(
                    ElementIdentityOccurrence(
                        page_index=page.page_index,
                        collection=collection,
                    )
                )

    violations: list[DuplicateElementIdentity] = []
    for element_id, occurrences in sorted(occurrences_by_id.items()):
        ordered = tuple(sorted(occurrences))
        if not element_id or len(ordered) > 1:
            violations.append(
                DuplicateElementIdentity(
                    element_id=element_id,
                    occurrences=ordered,
                )
            )

    return violations
