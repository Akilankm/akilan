from __future__ import annotations

import json
from pathlib import Path

from akilan.artifact_directory_integrity_cli import main


def test_cli_accepts_complete_artifact_and_persists_report(tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    (artifact / "document.json").write_text('{"schema_version":"1.0.0"}\n', encoding="utf-8")
    assets = artifact / "assets"
    assets.mkdir()
    (assets / "sample.bin").write_bytes(b"sample")
    report_path = tmp_path / "reports" / "integrity.json"

    assert main([str(artifact), "--report", str(report_path)]) == 0

    emitted = json.loads(capsys.readouterr().out)
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert emitted == persisted
    assert emitted["accepted"] is True
    assert emitted["file_count"] == 2
    assert len(emitted["fingerprint"]) == 64
    assert [item["relative_path"] for item in emitted["files"]] == [
        "assets/sample.bin",
        "document.json",
    ]


def test_cli_rejects_incomplete_artifact_on_stderr(tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "artifact"
    artifact.mkdir()

    assert main([str(artifact)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["accepted"] is False
    assert payload["status"] == "missing_document"
    assert payload["files"] == []


def test_cli_report_changes_when_any_artifact_byte_changes(tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    document = artifact / "document.json"
    document.write_text('{"schema_version":"1.0.0"}\n', encoding="utf-8")

    assert main([str(artifact)]) == 0
    first = json.loads(capsys.readouterr().out)

    document.write_text('{ "schema_version": "1.0.0" }\n', encoding="utf-8")
    assert main([str(artifact)]) == 0
    second = json.loads(capsys.readouterr().out)

    assert first["fingerprint"] != second["fingerprint"]
