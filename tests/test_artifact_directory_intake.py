from __future__ import annotations

import json

import akilan.artifact_directory_intake as intake_module
from akilan import ArtifactDirectoryIntakeReport, assess_artifact_directory_intake


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


def test_valid_complete_directory_is_accepted_through_public_api(tmp_path) -> None:
    root = tmp_path / "artifact"
    write_artifact(root, valid_artifact())

    report = assess_artifact_directory_intake(root)

    assert isinstance(report, ArtifactDirectoryIntakeReport)
    assert report.accepted is True
    assert report.status == "accepted"
    assert report.integrity.file_count == 2
    assert report.intake is not None
    assert report.intake.accepted is True


def test_invalid_projection_integrity_fails_before_document_intake(tmp_path) -> None:
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "projection.md").write_text("orphan", encoding="utf-8")

    report = assess_artifact_directory_intake(root)

    assert report.accepted is False
    assert report.status == "integrity_rejected"
    assert report.integrity.status == "missing_document"
    assert report.intake is None


def test_incompatible_document_preserves_complete_integrity_evidence(tmp_path) -> None:
    root = tmp_path / "artifact"
    artifact = valid_artifact()
    artifact["schema_version"] = "2.0.0"
    write_artifact(root, artifact)

    report = assess_artifact_directory_intake(root)

    assert report.accepted is False
    assert report.status == "artifact_rejected"
    assert report.integrity.accepted is True
    assert report.intake is not None
    assert report.intake.compatibility.status.value == "unsupported_major"


def test_document_change_after_integrity_is_rejected(tmp_path, monkeypatch) -> None:
    root = tmp_path / "artifact"
    write_artifact(root, valid_artifact())
    original = intake_module.assess_artifact_directory_integrity

    def mutate_after_integrity(path):
        report = original(path)
        (root / "document.json").write_text("{}", encoding="utf-8")
        return report

    monkeypatch.setattr(
        intake_module,
        "assess_artifact_directory_integrity",
        mutate_after_integrity,
    )

    report = assess_artifact_directory_intake(root)

    assert report.accepted is False
    assert report.status == "changed_after_integrity"
    assert report.intake is None


def test_non_object_document_root_fails_closed(tmp_path) -> None:
    root = tmp_path / "artifact"
    write_artifact(root, [])

    report = assess_artifact_directory_intake(root)

    assert report.accepted is False
    assert report.status == "invalid_document_root"
    assert report.intake is None
