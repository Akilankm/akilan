from __future__ import annotations

import json
from pathlib import Path

from akilan.artifact_intake_batch_cli import main


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


def write_artifact(directory: Path, artifact: object) -> None:
    directory.mkdir(parents=True)
    (directory / "document.json").write_text(json.dumps(artifact), encoding="utf-8")


def write_manifest(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_valid_manifest_is_accepted_in_identifier_order(tmp_path, capsys) -> None:
    write_artifact(tmp_path / "alpha", valid_artifact())
    write_artifact(tmp_path / "zeta", valid_artifact())
    manifest = tmp_path / "artifacts.json"
    write_manifest(manifest, {"zeta": "zeta", "alpha": "alpha"})
    report = tmp_path / "intake.json"

    exit_code = main([str(manifest), "--report", str(report)])

    payload = json.loads(capsys.readouterr().out)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["accepted"] is True
    assert payload["accepted_count"] == 2
    assert [entry["artifact_id"] for entry in payload["entries"]] == ["alpha", "zeta"]
    assert len(payload["fingerprint"]) == 64
    assert persisted["fingerprint"] == payload["fingerprint"]


def test_missing_member_rejects_complete_manifest_without_subset_acceptance(tmp_path, capsys) -> None:
    write_artifact(tmp_path / "present", valid_artifact())
    manifest = tmp_path / "artifacts.json"
    write_manifest(manifest, {"present": "present", "missing": "missing"})

    exit_code = main([str(manifest)])

    payload = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert payload["accepted"] is False
    assert payload["total_count"] == 2
    assert payload["accepted_count"] == 1
    assert payload["rejected_count"] == 1
    missing = next(entry for entry in payload["entries"] if entry["artifact_id"] == "missing")
    assert missing["status"] == "missing"


def test_incompatible_member_preserves_actionable_evidence(tmp_path, capsys) -> None:
    artifact = valid_artifact()
    artifact["schema_version"] = "2.0.0"
    write_artifact(tmp_path / "future", artifact)
    manifest = tmp_path / "artifacts.json"
    write_manifest(manifest, {"future": "future"})

    exit_code = main([str(manifest)])

    payload = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert payload["entries"][0]["compatibility"]["status"] == "unsupported_major"


def test_empty_and_invalid_manifests_fail_closed(tmp_path, capsys) -> None:
    empty = tmp_path / "empty.json"
    write_manifest(empty, {})
    assert main([str(empty)]) == 1
    assert json.loads(capsys.readouterr().err)["total_count"] == 0

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{bad-json", encoding="utf-8")
    assert main([str(malformed)]) == 1
    assert json.loads(capsys.readouterr().err)["status"] == "invalid_json"
