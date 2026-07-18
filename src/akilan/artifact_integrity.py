"""Document-level integrity checks for persisted AKILAN artifacts.

These checks complement :mod:`akilan.schema`, which validates the canonical
shape and page-local reference graph. They focus on invariants that require a
whole-document view and therefore matter for partial extraction, incremental
builds, cache reuse, and downstream page joins.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .schema import ArtifactSchemaError, SchemaViolation


def validate_page_identities(
    artifact: Mapping[str, Any], *, raise_on_error: bool = True
) -> list[SchemaViolation]:
    """Validate ordered, unique, source-stable page identities.

    A valid page identity graph satisfies all of the following:

    - ``page_index`` is a non-negative integer;
    - ``page_number`` is a positive integer;
    - ``page_number == page_index + 1``;
    - page indexes and numbers are unique;
    - pages are serialized in strictly increasing source order.

    Non-contiguous identities are intentionally accepted so page-range and
    resumable extraction can preserve original source coordinates.
    """

    violations: list[SchemaViolation] = []
    pages = artifact.get("pages")
    if not _is_sequence(pages):
        return _finish(violations, raise_on_error)

    seen_indexes: dict[int, str] = {}
    seen_numbers: dict[int, str] = {}
    previous_index: int | None = None

    for position, page in enumerate(pages):
        path = f"$.pages[{position}]"
        if not isinstance(page, Mapping):
            continue

        page_index = page.get("page_index")
        page_number = page.get("page_number")
        valid_index = isinstance(page_index, int) and not isinstance(page_index, bool) and page_index >= 0
        valid_number = isinstance(page_number, int) and not isinstance(page_number, bool) and page_number > 0

        if not valid_index or not valid_number:
            continue

        expected_number = page_index + 1
        if page_number != expected_number:
            violations.append(
                SchemaViolation(
                    f"{path}.page_number",
                    f"must equal page_index + 1 ({expected_number}), got {page_number}",
                )
            )

        first_index_path = seen_indexes.get(page_index)
        if first_index_path is not None:
            violations.append(
                SchemaViolation(
                    f"{path}.page_index",
                    f"duplicates source page index {page_index} first declared at {first_index_path}",
                )
            )
        else:
            seen_indexes[page_index] = f"{path}.page_index"

        first_number_path = seen_numbers.get(page_number)
        if first_number_path is not None:
            violations.append(
                SchemaViolation(
                    f"{path}.page_number",
                    f"duplicates source page number {page_number} first declared at {first_number_path}",
                )
            )
        else:
            seen_numbers[page_number] = f"{path}.page_number"

        if previous_index is not None and page_index <= previous_index:
            violations.append(
                SchemaViolation(
                    f"{path}.page_index",
                    f"must be greater than previous source page index {previous_index}",
                )
            )
        previous_index = page_index

    return _finish(violations, raise_on_error)


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _finish(violations: list[SchemaViolation], raise_on_error: bool) -> list[SchemaViolation]:
    if violations and raise_on_error:
        raise ArtifactSchemaError(violations)
    return violations
