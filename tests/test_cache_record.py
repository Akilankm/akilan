from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from akilan import (
    ExtractionConfig,
    build_artifact,
    resolve_artifact_cache,
    validate_artifact_cache,
)
from akilan.cache_record import CACHE_RECORD_NAME


def _write_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "cache completeness fixture")
    document.save(path)
    document.close()


def test_completed_build_is_a_valid_cache_hit(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)

    build_artifact(source, output)
    validation = validate_artifact_cache(source, output)

    assert validation.hit is True
    assert validation.reasons == ()
    record = json.loads((output / CACHE_RECORD_NAME).read_text(encoding="utf-8"))
    assert record["state"] == "complete"
    assert record["identity"] == validation.identity.to_dict()


def test_cache_miss_when_configuration_changes(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    build_artifact(source, output)

    validation = validate_artifact_cache(source, output, ExtractionConfig(render_pages=True))

    assert validation.hit is False
    assert validation.reasons == ("cache identity does not match the current extraction request",)


def test_cache_miss_when_completion_record_is_missing(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    build_artifact(source, output)
    (output / CACHE_RECORD_NAME).unlink()

    validation = validate_artifact_cache(source, output)

    assert validation.hit is False
    assert validation.reasons == ("cache completion record is missing",)


def test_cache_miss_when_artifact_is_incomplete(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    build_artifact(source, output)
    (output / "document.json").unlink()

    validation = validate_artifact_cache(source, output)

    assert validation.hit is False
    assert validation.reasons == ("artifact directory validation failed with 1 violation(s)",)


def test_cache_validation_does_not_mutate_artifact(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    build_artifact(source, output)
    before = {path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()}

    first = validate_artifact_cache(source, output)
    second = validate_artifact_cache(source, output)
    after = {path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()}

    assert first == second
    assert before == after


def test_cache_resolver_returns_validated_canonical_document(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    build_artifact(source, output)

    resolution = resolve_artifact_cache(source, output)

    assert resolution.hit is True
    assert resolution.reasons == ()
    assert resolution.artifact is not None
    assert resolution.artifact["source"]["file_name"] == "source.pdf"
    assert resolution.artifact["pages"][0]["page_number"] == 1


def test_cache_resolver_returns_none_for_normal_cache_miss(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)

    resolution = resolve_artifact_cache(source, output)

    assert resolution.hit is False
    assert resolution.artifact is None
    assert resolution.reasons == (
        "cache completion record is missing",
        "artifact directory validation failed with 1 violation(s)",
    )


def test_cache_resolver_returns_detached_payload(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "artifact"
    _write_pdf(source)
    build_artifact(source, output)
    before = (output / "document.json").read_bytes()

    first = resolve_artifact_cache(source, output)
    assert first.artifact is not None
    first.artifact["source"]["file_name"] = "mutated.pdf"
    second = resolve_artifact_cache(source, output)

    assert second.hit is True
    assert second.artifact is not None
    assert second.artifact["source"]["file_name"] == "source.pdf"
    assert (output / "document.json").read_bytes() == before
