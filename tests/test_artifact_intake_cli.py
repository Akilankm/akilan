from __future__ import annotations

import json

from akilan.artifact_intake_cli import main


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


def write_artifact(path, artifact: object) -> None:
    path.write_text(json.dumps(artifact), encoding="utf-8")


def test_valid_artifact_directory_returns_zero_and_writes_report(tmp_path, capsys) -> None:
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    write_artifact(artifact_dir / "document.json", valid_artifact())
    report_path = tmp_path / "intake.json"

    exit_code = main([str(artifact_dir), "--report", str(report_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["accepted"] is True
    assert payload["status"] == "accepted"
    assert payload["source_path"] == str((artifact_dir / "document.json").resolve())
    assert payload["report"] == str(report_path.resolve())
    assert persisted["accepted"] is True
    assert persisted["compatibility"]["status"] == "compatible"


def test_incompatible_artifact_fails_closed_on_stderr(tmp_path, capsys) -> None:
    artifact = valid_artifact()
    artifact["schema_version"] = "2.0.0"
    source = tmp_path / "document.json"
    write_artifact(source, artifact)

    exit_code = main([str(source)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["accepted"] is False
    assert payload["status"] == "rejected"
    assert payload["compatibility"]["status"] == "unsupported_major"


def test_invalid_json_fails_closed_and_persists_evidence(tmp_path, capsys) -> None:
    source = tmp_path / "document.json"
    source.write_text("{not-json", encoding="utf-8")
    report_path = tmp_path / "rejected.json"

    exit_code = main([str(source), "--report", str(report_path)])

    payload = json.loads(capsys.readouterr().err)
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["status"] == "invalid_json"
    assert payload["message"] == "artifact document is not valid JSON"
    assert persisted["status"] == "invalid_json"
    assert persisted["compatibility"] is None


def test_non_object_json_root_is_rejected(tmp_path, capsys) -> None:
    source = tmp_path / "document.json"
    write_artifact(source, [])

    exit_code = main([str(source)])

    payload = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert payload["status"] == "invalid_root"
    assert payload["message"] == "artifact JSON root must be an object"


def test_missing_artifact_is_rejected_without_traceback(tmp_path, capsys) -> None:
    source = tmp_path / "missing" / "document.json"

    exit_code = main([str(source)])

    payload = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert payload["status"] == "missing"
    assert payload["source_path"] == str(source.resolve())
