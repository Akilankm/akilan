from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from akilan import ArtifactSchemaError, ExtractionConfig, PDFArtifactBuilder, validate_artifact_directory


def _build_artifact(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "source.pdf"
    document = pymupdf.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((30, 40), "Persisted artifact integrity")
    document.save(pdf_path)
    document.close()

    output = tmp_path / "artifact"
    PDFArtifactBuilder(ExtractionConfig(overwrite=True)).build(pdf_path, output)
    return output


def test_validate_artifact_directory_accepts_complete_builder_output(tmp_path: Path) -> None:
    output = _build_artifact(tmp_path)

    assert validate_artifact_directory(output) == []


def test_validate_artifact_directory_reports_missing_declared_files(tmp_path: Path) -> None:
    output = _build_artifact(tmp_path)
    (output / "pages" / "page_0001.json").unlink()

    violations = validate_artifact_directory(output, raise_on_error=False)

    assert any(
        violation.path == "$.artifact_files.pages[0]" and "missing" in violation.message
        for violation in violations
    )


def test_validate_artifact_directory_rejects_path_traversal(tmp_path: Path) -> None:
    output = _build_artifact(tmp_path)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_files"]["document_json"] = "../document.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ArtifactSchemaError) as captured:
        validate_artifact_directory(output)

    assert any(
        violation.path == "$.artifact_files.document_json" and "safe" in violation.message
        for violation in captured.value.violations
    )


def test_validate_artifact_directory_aggregates_json_and_storage_failures(tmp_path: Path) -> None:
    output = _build_artifact(tmp_path)
    (output / "document.json").write_text("not-json", encoding="utf-8")
    (output / "pages" / "page_0001.json").unlink()

    violations = validate_artifact_directory(output, raise_on_error=False)

    paths = {violation.path for violation in violations}
    assert "$.document_json" in paths
    assert "$.artifact_files.pages[0]" in paths


def test_validate_artifact_directory_rejects_manifest_document_drift(tmp_path: Path) -> None:
    output = _build_artifact(tmp_path)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["size_bytes"] += 1
    manifest["pages"][0]["label"] = "tampered"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    violations = validate_artifact_directory(output, raise_on_error=False)

    paths = {violation.path for violation in violations}
    assert "$.manifest.source" in paths
    assert "$.manifest.pages[0].label" in paths


def test_validate_artifact_directory_rejects_page_file_drift(tmp_path: Path) -> None:
    output = _build_artifact(tmp_path)
    page_path = output / "pages" / "page_0001.json"
    page = json.loads(page_path.read_text(encoding="utf-8"))
    page["label"] = "mutated-page-copy"
    page_path.write_text(json.dumps(page), encoding="utf-8")

    violations = validate_artifact_directory(output, raise_on_error=False)

    assert any(
        violation.path == "$.page_json[0]" and "exactly match" in violation.message
        for violation in violations
    )


def test_validate_artifact_directory_rejects_declared_page_path_drift(tmp_path: Path) -> None:
    output = _build_artifact(tmp_path)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    original_page = output / manifest["artifact_files"]["pages"][0]
    alternate_page = output / "pages" / "alternate.json"
    alternate_page.write_bytes(original_page.read_bytes())
    manifest["artifact_files"]["pages"][0] = "pages/alternate.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    violations = validate_artifact_directory(output, raise_on_error=False)

    assert any(
        violation.path == "$.artifact_files.pages[0]" and "json_path" in violation.message
        for violation in violations
    )


def test_validate_artifact_directory_reports_missing_root(tmp_path: Path) -> None:
    violations = validate_artifact_directory(tmp_path / "missing", raise_on_error=False)

    assert len(violations) == 1
    assert violations[0].path == "$"
    assert "does not exist" in violations[0].message
