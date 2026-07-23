"""Semantic validation for persisted AKILAN document graphs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

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
class PersistedGraphViolation:
    """One deterministic semantic violation in a persisted document graph."""

    path: str
    message: str
    rule_id: str

    def to_dict(self) -> dict[str, str]:
        """Return stable machine-readable evidence."""

        return {
            "path": self.path,
            "message": self.message,
            "rule_id": self.rule_id,
        }


def _pages(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = document.get("pages", [])
    if not isinstance(value, list):
        return []
    return [page for page in value if isinstance(page, Mapping)]


def _elements(page: Mapping[str, Any]) -> list[tuple[str, int, Mapping[str, Any]]]:
    elements: list[tuple[str, int, Mapping[str, Any]]] = []
    for collection in _ELEMENT_COLLECTIONS:
        value = page.get(collection, [])
        if not isinstance(value, list):
            continue
        for index, element in enumerate(value):
            if isinstance(element, Mapping):
                elements.append((collection, index, element))
    return elements


def find_persisted_graph_violations(
    document: Mapping[str, Any],
) -> list[PersistedGraphViolation]:
    """Validate document-wide element identity and relationship references.

    Structural schema validation is expected to run first. This function remains
    defensive so callers can use it independently without receiving type errors.
    The input mapping is never mutated.
    """

    indexed: list[tuple[str, str, Mapping[str, Any]]] = []
    locations_by_id: dict[str, list[str]] = {}

    for page_position, page in enumerate(_pages(document)):
        page_index = page.get("page_index", page_position)
        page_path = f"$.pages[{page_position}]"
        for collection, element_position, element in _elements(page):
            path = f"{page_path}.{collection}[{element_position}]"
            raw_id = element.get("id")
            element_id = raw_id if isinstance(raw_id, str) else ""
            indexed.append((path, element_id, element))
            locations_by_id.setdefault(element_id, []).append(
                f"page_index={page_index}, path={path}"
            )

    violations: list[PersistedGraphViolation] = []
    for element_id, locations in sorted(locations_by_id.items()):
        ordered_locations = sorted(locations)
        if not element_id:
            for location in ordered_locations:
                path = location.split("path=", maxsplit=1)[-1]
                violations.append(
                    PersistedGraphViolation(
                        path=f"{path}.id",
                        message="element ID must be a non-empty string",
                        rule_id="document-element-id-uniqueness-v1",
                    )
                )
        elif len(ordered_locations) > 1:
            locations_text = "; ".join(ordered_locations)
            for location in ordered_locations:
                path = location.split("path=", maxsplit=1)[-1]
                violations.append(
                    PersistedGraphViolation(
                        path=f"{path}.id",
                        message=(
                            f"element ID {element_id!r} is defined more than once: "
                            f"{locations_text}"
                        ),
                        rule_id="document-element-id-uniqueness-v1",
                    )
                )

    known_ids = {element_id for element_id in locations_by_id if element_id}
    for path, element_id, element in indexed:
        relationships = element.get("relationships", {})
        if not isinstance(relationships, Mapping):
            continue
        for relationship_name, targets in sorted(
            relationships.items(), key=lambda item: str(item[0])
        ):
            relationship_path = f"{path}.relationships[{relationship_name!r}]"
            if not isinstance(relationship_name, str) or not relationship_name.strip():
                violations.append(
                    PersistedGraphViolation(
                        path=relationship_path,
                        message="relationship name must be a non-empty string",
                        rule_id="relationship-target-integrity-v1",
                    )
                )
            if not isinstance(targets, list):
                continue

            seen: set[str] = set()
            for target_position, raw_target in enumerate(targets):
                target_path = f"{relationship_path}[{target_position}]"
                target = raw_target if isinstance(raw_target, str) else ""
                if not target:
                    violations.append(
                        PersistedGraphViolation(
                            path=target_path,
                            message="relationship target must be a non-empty string",
                            rule_id="relationship-target-integrity-v1",
                        )
                    )
                    continue
                if target == element_id:
                    violations.append(
                        PersistedGraphViolation(
                            path=target_path,
                            message="relationship target must not reference its source element",
                            rule_id="relationship-target-integrity-v1",
                        )
                    )
                if target in seen:
                    violations.append(
                        PersistedGraphViolation(
                            path=target_path,
                            message=f"duplicate relationship target {target!r}",
                            rule_id="relationship-target-integrity-v1",
                        )
                    )
                seen.add(target)
                if target not in known_ids:
                    violations.append(
                        PersistedGraphViolation(
                            path=target_path,
                            message=f"relationship target {target!r} does not exist",
                            rule_id="relationship-target-integrity-v1",
                        )
                    )

    return sorted(violations)
