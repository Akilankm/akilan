from __future__ import annotations

import copy

import pytest

from akilan.artifact_intake_batch import assess_artifact_batch_intake


def valid_artifact() -> dict[str, object]:
    bbox = {"x0": 0.0, "y0": 0.0, "x1": 100.0, "y1": 200.0}
    return {
        "schema_version": "1.0.0",
        "generator": {},
        "source": {},
        "document": {},
        "table_of_contents": [],
        "embedded_files": [],
        "pages": [
            {
                "page_index": 0,
                "page_number": 1,
                "label": "1",
                "width": 100.0,
                "height": 200.0,
                "rotation": 0,
                "mediabox": bbox,
                "cropbox": bbox,
                "text_blocks": [],
                "tables": [],
                "images": [],
                "drawings": [],
                "links": [],
                "annotations": [],
                "widgets": [],
                "reading_order": [],
                "metrics": {},
            }
        ],
        "statistics": {},
        "artifact_files": {},
    }


def test_batch_is_ordered_deterministic_and_accepted() -> None:
    artifacts = {"zeta": valid_artifact(), "alpha": valid_artifact()}

    first = assess_artifact_batch_intake(artifacts)
    second = assess_artifact_batch_intake(dict(reversed(list(artifacts.items()))))

    assert first.accepted is True
    assert first.total_count == 2
    assert first.accepted_count == 2
    assert first.rejected_count == 0
    assert [entry.artifact_id for entry in first.entries] == ["alpha", "zeta"]
    assert first.fingerprint == second.fingerprint
    assert first.to_dict() == second.to_dict()


def test_batch_fails_closed_when_any_member_is_rejected() -> None:
    rejected = valid_artifact()
    rejected["schema_version"] = "2.0.0"

    report = assess_artifact_batch_intake(
        {"accepted": valid_artifact(), "rejected": rejected}
    )

    assert report.accepted is False
    assert report.accepted_count == 1
    assert report.rejected_count == 1
    assert report.entries[1].report.compatibility.status.value == "unsupported_major"


def test_empty_batch_is_rejected_with_stable_evidence() -> None:
    report = assess_artifact_batch_intake({})

    assert report.accepted is False
    assert report.total_count == 0
    assert report.rejected_count == 0
    assert len(report.fingerprint) == 64


def test_batch_does_not_mutate_artifacts() -> None:
    artifacts = {"artifact": valid_artifact()}
    before = copy.deepcopy(artifacts)

    assess_artifact_batch_intake(artifacts)

    assert artifacts == before


@pytest.mark.parametrize("artifact_id", ["", 1])
def test_invalid_artifact_identifiers_are_rejected(artifact_id: object) -> None:
    with pytest.raises(ValueError, match="non-empty strings"):
        assess_artifact_batch_intake({artifact_id: valid_artifact()})  # type: ignore[dict-item]
