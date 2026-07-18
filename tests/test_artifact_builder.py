from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from akilan import ExtractionConfig, PDFArtifactBuilder


def _make_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((50, 40), "ACME RESEARCH", fontsize=8)
    page.insert_text((50, 95), "Geometry-Aware PDF Analysis", fontsize=22, fontname="helv")
    page.insert_text((50, 135), "1. Introduction", fontsize=15, fontname="hebo")
    page.insert_textbox(
        pymupdf.Rect(50, 155, 540, 220),
        "AKILAN preserves text, geometry, tables, images and vector drawings.",
        fontsize=11,
    )
    page.insert_text((60, 250), "Name", fontsize=9)
    page.insert_text((260, 250), "Score", fontsize=9)
    page.insert_text((60, 280), "Ada", fontsize=9)
    page.insert_text((260, 280), "98", fontsize=9)
    for x in (50, 240, 340):
        page.draw_line((x, 230), (x, 300), color=(0, 0, 0), width=0.8)
    for y in (230, 260, 300):
        page.draw_line((50, y), (340, y), color=(0, 0, 0), width=0.8)
    page.draw_rect(pymupdf.Rect(390, 235, 520, 330), color=(0.1, 0.2, 0.7), fill=(0.9, 0.9, 1.0))
    page.insert_text((410, 285), "VECTOR", fontsize=12)
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(50, 330, 180, 350), "uri": "https://example.com"})
    page.insert_text((50, 820), "1", fontsize=8)

    second = document.new_page(width=595, height=842)
    second.insert_text((50, 40), "ACME RESEARCH", fontsize=8)
    second.insert_text((50, 95), "2. Details", fontsize=15, fontname="hebo")
    second.insert_textbox(pymupdf.Rect(50, 125, 540, 190), "Second-page body text.", fontsize=11)
    second.insert_text((50, 820), "2", fontsize=8)
    document.save(path)
    document.close()


def test_builder_creates_complete_artifact(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    output = tmp_path / "artifact"
    _make_pdf(pdf)

    artifact = PDFArtifactBuilder(
        ExtractionConfig(render_pages=True, overwrite=True)
    ).build(pdf, output)

    assert artifact.statistics["page_count"] == 2
    assert artifact.statistics["text_block_count"] >= 6
    assert artifact.statistics["drawing_count"] > 0
    assert artifact.statistics["link_count"] == 1
    assert (output / "manifest.json").is_file()
    assert (output / "document.json").is_file()
    assert (output / "document.md").is_file()
    assert (output / "document.txt").is_file()
    assert (output / "pages/page_0001.json").is_file()
    assert (output / "assets/renders/page_0001.png").is_file()

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["source"]["sha256"]

    page = json.loads((output / "pages/page_0001.json").read_text(encoding="utf-8"))
    roles = {block["semantic_role"] for block in page["text_blocks"]}
    assert "document_title" in roles
    assert page["reading_order"]


def test_builder_protects_nonempty_output(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    output = tmp_path / "artifact"
    _make_pdf(pdf)
    output.mkdir()
    (output / "keep.txt").write_text("do not delete", encoding="utf-8")

    builder = PDFArtifactBuilder(ExtractionConfig(overwrite=False))
    with pytest.raises(FileExistsError):
        builder.build(pdf, output)


def test_failed_overwrite_preserves_last_known_good_artifact(tmp_path: Path) -> None:
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_bytes(b"not a pdf")
    output = tmp_path / "artifact"
    output.mkdir()
    marker = output / "known-good.txt"
    marker.write_text("preserve me", encoding="utf-8")

    builder = PDFArtifactBuilder(ExtractionConfig(overwrite=True))
    with pytest.raises(Exception):
        builder.build(invalid_pdf, output)

    assert marker.read_text(encoding="utf-8") == "preserve me"
    assert not list(tmp_path.glob(".artifact.akilan-*.tmp"))
    assert not list(tmp_path.glob(".artifact.akilan-*.bak"))


def test_successful_overwrite_replaces_previous_artifact_atomically(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    output = tmp_path / "artifact"
    _make_pdf(pdf)
    output.mkdir()
    stale = output / "stale.txt"
    stale.write_text("old", encoding="utf-8")

    PDFArtifactBuilder(ExtractionConfig(overwrite=True)).build(pdf, output)

    assert not stale.exists()
    assert (output / "manifest.json").is_file()
    assert not list(tmp_path.glob(".artifact.akilan-*.tmp"))
    assert not list(tmp_path.glob(".artifact.akilan-*.bak"))
