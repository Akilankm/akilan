from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from akilan.benchmark import run_corpus
from akilan.benchmark_cache_validation import validate_benchmark_cache_entry
from akilan.config import ExtractionConfig


def _write_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((30, 40), "benchmark cache integrity")
    document.save(path)
    document.close()


def _build_cache_entry(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    pdf_path = tmp_path / "source.pdf"
    _write_pdf(pdf_path)
    case = run_corpus(
        [pdf_path],
        tmp_path / "artifacts",
        config=ExtractionConfig(overwrite=True),
    ).cases[0]
    root = Path(case.output_dir)
    marker = json.loads((root / ".akilan-benchmark-cache.json").read_text(encoding="utf-8"))
    return root, marker


def _write_marker(root: Path, marker: dict[str, object]) -> None:
    (root / ".akilan-benchmark-cache.json").write_text(
        json.dumps(marker, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_valid_benchmark_cache_entry_has_no_violations(tmp_path: Path) -> None:
    root, marker = _build_cache_entry(tmp_path)

    assert validate_benchmark_cache_entry(root) == []
    assert validate_benchmark_cache_entry(root, expected_identity=str(marker["identity"])) == []


def test_missing_artifact_file_invalidates_benchmark_cache(tmp_path: Path) -> None:
    root, _ = _build_cache_entry(tmp_path)
    (root / "document.json").unlink()

    violations = validate_benchmark_cache_entry(root)

    assert any(violation.path.startswith("$.artifact") for violation in violations)
    assert any("missing" in violation.message for violation in violations)


def test_cached_metrics_must_match_persisted_document(tmp_path: Path) -> None:
    root, marker = _build_cache_entry(tmp_path)
    marker["metrics"]["source_sha256"] = "0" * 64
    marker["metrics"]["page_count"] = 999
    marker["metrics"]["artifact_fingerprint"] = "not-a-digest"
    _write_marker(root, marker)

    violations = validate_benchmark_cache_entry(root)
    paths = [violation.path for violation in violations]

    assert "$.cache.metrics.source_sha256" in paths
    assert "$.cache.metrics.page_count" in paths
    assert "$.cache.metrics.artifact_fingerprint" in paths


def test_schema_valid_content_tampering_invalidates_fingerprint(tmp_path: Path) -> None:
    root, _ = _build_cache_entry(tmp_path)
    document_path = root / "document.json"
    document = json.loads(document_path.read_text(encoding="utf-8"))
    page = document["pages"][0]
    page["text_blocks"][0]["lines"][0]["spans"][0]["text"] = "tampered content"
    _write_json(document_path, document)
    _write_json(root / page["json_path"], page)

    violations = validate_benchmark_cache_entry(root)

    assert any(
        violation.path == "$.cache.metrics.artifact_fingerprint"
        and violation.message == "must match the canonical fingerprint of document.json"
        for violation in violations
    )
    assert not any(violation.path.startswith("$.artifact") for violation in violations)


def test_marker_format_version_is_required_and_supported(tmp_path: Path) -> None:
    root, marker = _build_cache_entry(tmp_path)
    marker["cache_format_version"] = 2
    _write_marker(root, marker)

    violations = validate_benchmark_cache_entry(root)

    assert any(
        violation.path == "$.cache.cache_format_version"
        and "unsupported version 2" in violation.message
        for violation in violations
    )

    marker["cache_format_version"] = True
    _write_marker(root, marker)
    violations = validate_benchmark_cache_entry(root)

    assert any(
        violation.path == "$.cache.cache_format_version"
        and violation.message == "must be an integer"
        for violation in violations
    )


def test_marker_identity_and_metric_shapes_are_validated(tmp_path: Path) -> None:
    root, marker = _build_cache_entry(tmp_path)
    marker["identity"] = "not-a-digest"
    marker["metrics"]["source_sha256"] = "ABC"
    marker["metrics"]["page_count"] = True
    _write_marker(root, marker)

    violations = validate_benchmark_cache_entry(root)
    evidence = {(violation.path, violation.message) for violation in violations}

    assert (
        "$.cache.identity",
        "must be a lowercase 64-character SHA-256 digest",
    ) in evidence
    assert (
        "$.cache.metrics.source_sha256",
        "must be a lowercase 64-character SHA-256 digest",
    ) in evidence
    assert (
        "$.cache.metrics.page_count",
        "must be a non-negative integer",
    ) in evidence


def test_expected_identity_mismatch_is_reported_without_mutation(tmp_path: Path) -> None:
    root, _ = _build_cache_entry(tmp_path)
    marker_path = root / ".akilan-benchmark-cache.json"
    before = marker_path.read_bytes()

    first = validate_benchmark_cache_entry(root, expected_identity="different")
    second = validate_benchmark_cache_entry(root, expected_identity="different")

    assert first == second
    assert marker_path.read_bytes() == before
    assert first[0].path == "$.cache.identity"
    assert all(violation.rule_id == "benchmark-cache-integrity-v1" for violation in first)


def test_corrupt_marker_produces_actionable_location(tmp_path: Path) -> None:
    root, _ = _build_cache_entry(tmp_path)
    (root / ".akilan-benchmark-cache.json").write_text("not-json", encoding="utf-8")

    violations = validate_benchmark_cache_entry(root)

    assert len(violations) == 1
    assert violations[0].path == "$.cache"
    assert "invalid JSON" in violations[0].message
