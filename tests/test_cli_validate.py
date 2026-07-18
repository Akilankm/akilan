from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from akilan import ExtractionConfig, PDFArtifactBuilder
from akilan.cli import main


def _write_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "CLI artifact validation")
    document.save(path)
    document.close()


def test_validate_command_reports_valid_artifact(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    PDFArtifactBuilder(ExtractionConfig(overwrite=True)).build(source, output)

    exit_code = main(["validate", str(output)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload == {
        "artifact": str(output.resolve()),
        "valid": True,
        "schema_version": "1.0.0",
        "pages": 1,
        "violation_count": 0,
    }


def test_validate_command_reports_all_actionable_violations(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    PDFArtifactBuilder(ExtractionConfig(overwrite=True)).build(source, output)
    (output / "document.json").write_text("{not-json", encoding="utf-8")
    (output / "document.md").unlink()

    exit_code = main(["validate", str(output)])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exit_code == 1
    assert captured.out == ""
    assert payload["artifact"] == str(output.resolve())
    assert payload["valid"] is False
    assert payload["violation_count"] >= 2
    paths = {violation["path"] for violation in payload["violations"]}
    assert "$.artifact_files.document_markdown" in paths
    assert "$.document_json" in paths


def test_validate_command_rejects_missing_artifact_directory(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing"

    exit_code = main(["validate", str(missing)])

    payload = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert payload["valid"] is False
    assert payload["violation_count"] >= 1
    assert payload["violations"][0]["path"] == "$"
