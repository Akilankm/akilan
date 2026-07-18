from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from akilan import ArtifactSchemaError, ExtractionConfig, PDFArtifactBuilder, load_artifact_directory


def _write_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Validated artifact loader")
    document.save(path)
    document.close()


def test_load_artifact_directory_returns_validated_document(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)

    PDFArtifactBuilder(ExtractionConfig(overwrite=True)).build(source, output)

    loaded = load_artifact_directory(output)

    assert loaded["source"]["file_name"] == "source.pdf"
    assert loaded["document"]["page_count"] == 1
    assert loaded["pages"][0]["page_number"] == 1


def test_load_artifact_directory_rejects_corrupted_document(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    PDFArtifactBuilder(ExtractionConfig(overwrite=True)).build(source, output)
    (output / "document.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(ArtifactSchemaError) as exc_info:
        load_artifact_directory(output)

    assert "$.document_json" in str(exc_info.value)


def test_load_artifact_directory_honors_manifest_document_path(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    PDFArtifactBuilder(ExtractionConfig(overwrite=True)).build(source, output)

    original = output / "document.json"
    relocated = output / "canonical.json"
    original.replace(relocated)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_files"]["document_json"] = "canonical.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    loaded = load_artifact_directory(output)

    assert loaded["source"]["file_name"] == "source.pdf"
