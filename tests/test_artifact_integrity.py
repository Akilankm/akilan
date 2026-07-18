from __future__ import annotations

import pytest

from akilan.artifact_integrity import validate_page_identities
from akilan.schema import ArtifactSchemaError


def artifact_with_pages(*identities: tuple[int, int]) -> dict[str, object]:
    return {
        "pages": [
            {"page_index": page_index, "page_number": page_number}
            for page_index, page_number in identities
        ]
    }


def test_accepts_complete_and_non_contiguous_partial_page_sequences() -> None:
    assert validate_page_identities(artifact_with_pages((0, 1), (1, 2), (2, 3))) == []
    assert validate_page_identities(artifact_with_pages((1, 2), (4, 5), (9, 10))) == []


def test_collects_duplicate_and_descending_page_identity_violations() -> None:
    artifact = artifact_with_pages((0, 1), (2, 3), (0, 1))

    violations = validate_page_identities(artifact, raise_on_error=False)
    rendered = {str(violation) for violation in violations}

    assert (
        "$.pages[2].page_index: duplicates source page index 0 "
        "first declared at $.pages[0].page_index"
    ) in rendered
    assert (
        "$.pages[2].page_number: duplicates source page number 1 "
        "first declared at $.pages[0].page_number"
    ) in rendered
    assert "$.pages[2].page_index: must be greater than previous source page index 2" in rendered


def test_rejects_page_number_that_does_not_match_source_index() -> None:
    violations = validate_page_identities(
        artifact_with_pages((4, 4)),
        raise_on_error=False,
    )

    assert [str(violation) for violation in violations] == [
        "$.pages[0].page_number: must equal page_index + 1 (5), got 4"
    ]


def test_raises_schema_error_with_all_document_level_violations() -> None:
    with pytest.raises(ArtifactSchemaError) as error:
        validate_page_identities(artifact_with_pages((1, 2), (0, 4)))

    rendered = str(error.value)
    assert "$.pages[1].page_number: must equal page_index + 1 (1), got 4" in rendered
    assert "$.pages[1].page_index: must be greater than previous source page index 1" in rendered


def test_defers_shape_and_scalar_type_errors_to_canonical_schema_validator() -> None:
    artifact = {"pages": [None, {"page_index": True, "page_number": "1"}]}

    assert validate_page_identities(artifact) == []
