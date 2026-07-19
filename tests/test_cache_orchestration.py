from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from akilan import ExtractionConfig, build_or_resolve_artifact
from akilan.builder import PDFArtifactBuilder


def _write_pdf(path: Path, text: str) -> None:
    path.unlink(missing_ok=True)
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_build_or_resolve_builds_then_reuses_validated_artifact(tmp_path, monkeypatch):
    pdf_path = tmp_path / "source.pdf"
    output_dir = tmp_path / "artifact"
    _write_pdf(pdf_path, "cache orchestration")
    config = ExtractionConfig(overwrite=True)

    built = build_or_resolve_artifact(pdf_path, output_dir, config)

    assert built.cache_hit is False
    assert built.rebuilt is True
    assert "cache completion record is missing" in built.prior_miss_reasons
    assert any(
        reason.startswith("artifact directory validation failed with ")
        for reason in built.prior_miss_reasons
    )
    assert built.artifact == json.loads(
        (output_dir / "document.json").read_text(encoding="utf-8")
    )

    def fail_build(*args, **kwargs):
        raise AssertionError("builder must not run on a validated cache hit")

    monkeypatch.setattr(PDFArtifactBuilder, "build", fail_build)
    reused = build_or_resolve_artifact(pdf_path, output_dir, config)

    assert reused.cache_hit is True
    assert reused.rebuilt is False
    assert reused.prior_miss_reasons == ()
    assert reused.identity == built.identity
    assert reused.artifact == built.artifact


def test_build_or_resolve_rebuilds_when_source_identity_changes(tmp_path):
    pdf_path = tmp_path / "source.pdf"
    output_dir = tmp_path / "artifact"
    config = ExtractionConfig(overwrite=True)
    _write_pdf(pdf_path, "first source")

    first = build_or_resolve_artifact(pdf_path, output_dir, config)
    _write_pdf(pdf_path, "second source")
    second = build_or_resolve_artifact(pdf_path, output_dir, config)

    assert first.cache_hit is False
    assert second.cache_hit is False
    assert second.identity.key != first.identity.key
    assert (
        "cache identity does not match the current extraction request"
        in second.prior_miss_reasons
    )
    assert second.artifact["source"]["sha256"] == second.identity.source_sha256


def test_build_resolution_to_dict_is_stable_and_omits_artifact_payload(tmp_path):
    pdf_path = tmp_path / "source.pdf"
    output_dir = tmp_path / "artifact"
    _write_pdf(pdf_path, "operational evidence")

    result = build_or_resolve_artifact(pdf_path, output_dir)

    assert result.to_dict() == {
        "cache_hit": False,
        "rebuilt": True,
        "identity": result.identity.to_dict(),
        "prior_miss_reasons": list(result.prior_miss_reasons),
    }
    assert "artifact" not in result.to_dict()
