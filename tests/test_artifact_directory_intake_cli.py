from __future__ import annotations

import json
from pathlib import Path

from akilan.artifact_directory_intake_cli import main


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


def write_artifact(root: Path, artifact: object) -> None:
    root.mkdir()
    (root / "document.json").write_text(json.dumps(artifact, sort_keys=True), encoding="utf-8")
    (root / "document.md").write_text("# projection\n", encoding="utf-8")


def test_cli_accepts_complete_artifact_and_persists_report(tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "artifact"
    write_artifact(artifact, valid_artifact())
    report_path = tmp_path / "reports" / "intake.json"

    assert main([str(artifact), "--report", str(report_path)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    emitted = json.loads(captured.out)
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert emitted == persisted
    assert emitted["accepted"] is True
    assert emitted["status"] == "accepted"
    assert emitted["integrity"]["file_count"] == 2
    assert emitted["intake"]["accepted"] is True


def test_cli_rejects_incomplete_directory_on_stderr(tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "artifact"
    artifact.mkdir()

    assert main([str(artifact)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["accepted"] is False
    assert payload["status"] == "integrity_rejected"
    assert payload["integrity"]["status"] == "missing_document"
    assert payload["intake"] is None


def test_cli_rejects_incompatible_artifact_with_complete_integrity_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    artifact = tmp_path / "artifact"
    payload = valid_artifact()
    payload["schema_version"] = "2.0.0"
    write_artifact(artifact, payload)

    assert main([str(artifact)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    report = json.loads(captured.err)
    assert report["status"] == "artifact_rejected"
    assert report["integrity"]["accepted"] is True
    assert report["intake"]["compatibility"]["status"] == "unsupported_major"


def test_cli_rejects_invalid_document_json(tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    (artifact / "document.json").write_text("{", encoding="utf-8")

    assert main([str(artifact)]) == 1

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert payload["status"] == "invalid_document_json"
    assert payload["integrity"]["accepted"] is True
    assert payload["intake"] is None
