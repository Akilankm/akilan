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
    (root / ".akilan-benchmark-cache.json").write_text(
        json.dumps(marker, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    violations = validate_benchmark_cache_entry(root)
    paths = [violation.path for violation in violations]

    assert "$.cache.metrics.source_sha256" in paths
    assert "$.cache.metrics.page_count" in paths
    assert "$.cache.metrics.artifact_fingerprint" in paths


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
