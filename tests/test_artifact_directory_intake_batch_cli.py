from __future__ import annotations

import json

from akilan.artifact_directory_intake_batch_cli import main


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


def write_artifact(root) -> None:
    root.mkdir()
    (root / "document.json").write_text(
        json.dumps(valid_artifact(), sort_keys=True),
        encoding="utf-8",
    )
    (root / "document.md").write_text("# projection\n", encoding="utf-8")


def test_cli_accepts_manifest_defined_directories_and_persists_evidence(tmp_path, capsys) -> None:
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    write_artifact(alpha)
    write_artifact(beta)
    manifest = tmp_path / "artifacts.json"
    manifest.write_text(
        json.dumps({"beta": "beta", "alpha": "alpha"}),
        encoding="utf-8",
    )
    report = tmp_path / "reports" / "intake.json"

    exit_code = main([str(manifest), "--report", str(report)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert payload["accepted"] is True
    assert payload["total_count"] == 2
    assert payload["accepted_count"] == 2
    assert payload["rejected_count"] == 0
    assert [entry["identifier"] for entry in payload["entries"]] == ["alpha", "beta"]
    assert len(payload["fingerprint"]) == 64
    assert persisted == {key: value for key, value in payload.items() if key != "report"}


def test_cli_rejects_complete_batch_when_one_directory_is_invalid(tmp_path, capsys) -> None:
    valid = tmp_path / "valid"
    invalid = tmp_path / "invalid"
    write_artifact(valid)
    invalid.mkdir()
    (invalid / "projection.md").write_text("orphan", encoding="utf-8")
    manifest = tmp_path / "artifacts.json"
    manifest.write_text(
        json.dumps({"valid": "valid", "invalid": "invalid"}),
        encoding="utf-8",
    )

    exit_code = main([str(manifest)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["accepted"] is False
    assert payload["total_count"] == 2
    assert payload["accepted_count"] == 1
    assert payload["rejected_count"] == 1
    entries = {entry["identifier"]: entry for entry in payload["entries"]}
    assert entries["valid"]["accepted"] is True
    assert entries["invalid"]["report"]["status"] == "integrity_rejected"


def test_cli_rejects_empty_and_malformed_manifests(tmp_path, capsys) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    assert main([str(empty)]) == 1
    empty_payload = json.loads(capsys.readouterr().err)
    assert empty_payload["status"] == "empty_batch"

    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    assert main([str(malformed)]) == 1
    malformed_payload = json.loads(capsys.readouterr().err)
    assert malformed_payload["status"] == "invalid_json"


def test_cli_rejects_non_string_manifest_sources(tmp_path, capsys) -> None:
    manifest = tmp_path / "artifacts.json"
    manifest.write_text(json.dumps({"artifact": 42}), encoding="utf-8")

    assert main([str(manifest)]) == 1

    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "invalid_source"
    assert payload["entries"] == []
