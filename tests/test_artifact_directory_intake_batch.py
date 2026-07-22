from __future__ import annotations

import json

import pytest

from akilan import (
    ArtifactDirectoryBatchIntakeReport,
    assess_artifact_directory_batch_intake,
)


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


def write_artifact(root, artifact: object) -> None:
    root.mkdir()
    (root / "document.json").write_text(
        json.dumps(artifact, sort_keys=True),
        encoding="utf-8",
    )
    (root / "document.md").write_text("# projection\n", encoding="utf-8")


def test_valid_directory_set_is_accepted_in_identifier_order(tmp_path) -> None:
    alpha = tmp_path / "alpha"
    zeta = tmp_path / "zeta"
    write_artifact(alpha, valid_artifact())
    write_artifact(zeta, valid_artifact())

    report = assess_artifact_directory_batch_intake(
        {"zeta": zeta, "alpha": alpha},
    )

    assert isinstance(report, ArtifactDirectoryBatchIntakeReport)
    assert report.accepted is True
    assert report.status == "accepted"
    assert report.total_count == 2
    assert report.accepted_count == 2
    assert report.rejected_count == 0
    assert [entry.identifier for entry in report.entries] == ["alpha", "zeta"]
    assert len(report.fingerprint) == 64


def test_one_invalid_directory_rejects_complete_batch(tmp_path) -> None:
    valid = tmp_path / "valid"
    invalid = tmp_path / "invalid"
    write_artifact(valid, valid_artifact())
    invalid.mkdir()
    (invalid / "projection.md").write_text("orphan", encoding="utf-8")

    report = assess_artifact_directory_batch_intake(
        {"valid": valid, "invalid": invalid},
    )

    assert report.accepted is False
    assert report.status == "rejected"
    assert report.total_count == 2
    assert report.accepted_count == 1
    assert report.rejected_count == 1
    entries = {entry.identifier: entry for entry in report.entries}
    assert entries["valid"].accepted is True
    assert entries["invalid"].accepted is False
    assert entries["invalid"].report.status == "integrity_rejected"


def test_empty_directory_set_fails_closed_deterministically() -> None:
    first = assess_artifact_directory_batch_intake({})
    second = assess_artifact_directory_batch_intake({})

    assert first.accepted is False
    assert first.status == "empty_batch"
    assert first.total_count == 0
    assert first.fingerprint == second.fingerprint


def test_mapping_insertion_order_does_not_change_evidence(tmp_path) -> None:
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    write_artifact(alpha, valid_artifact())
    write_artifact(beta, valid_artifact())

    first = assess_artifact_directory_batch_intake({"beta": beta, "alpha": alpha})
    second = assess_artifact_directory_batch_intake({"alpha": alpha, "beta": beta})

    assert first.to_dict() == second.to_dict()


def test_fingerprint_changes_when_any_directory_bytes_change(tmp_path) -> None:
    root = tmp_path / "artifact"
    write_artifact(root, valid_artifact())
    before = assess_artifact_directory_batch_intake({"artifact": root})

    (root / "document.md").write_text("# changed projection\n", encoding="utf-8")
    after = assess_artifact_directory_batch_intake({"artifact": root})

    assert before.accepted is True
    assert after.accepted is True
    assert before.fingerprint != after.fingerprint


def test_empty_identifier_is_rejected_before_directory_access(tmp_path) -> None:
    with pytest.raises(ValueError, match="non-empty strings"):
        assess_artifact_directory_batch_intake({"": tmp_path / "artifact"})
