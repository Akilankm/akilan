from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from akilan.benchmark import run_corpus, write_corpus_report
from akilan.config import ExtractionConfig


def _write_pdf(path: Path, text: str) -> None:
    document = pymupdf.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((30, 40), text)
    document.save(path)
    document.close()


def test_measure_artifact_is_deterministic(tmp_path: Path) -> None:
    pdf_path = tmp_path / "simple.pdf"
    _write_pdf(pdf_path, "AKILAN benchmark")

    report = run_corpus(
        [pdf_path],
        tmp_path / "artifacts",
        config=ExtractionConfig(overwrite=True),
    )

    assert report.succeeded == 1
    assert report.failed == 0
    case = report.cases[0]
    assert case.metrics is not None
    assert case.metrics.page_count == 1
    assert case.metrics.text_block_count >= 1
    assert case.metrics.ordered_element_ratio == 1.0
    assert len(case.metrics.artifact_fingerprint) == 64

    second_report = run_corpus(
        [pdf_path],
        tmp_path / "artifacts-second",
        config=ExtractionConfig(overwrite=True),
    )
    second_metrics = second_report.cases[0].metrics
    assert second_metrics is not None
    assert second_metrics.artifact_fingerprint == case.metrics.artifact_fingerprint


def test_run_corpus_isolates_failures_and_writes_report(tmp_path: Path) -> None:
    valid_pdf = tmp_path / "valid.pdf"
    missing_pdf = tmp_path / "missing.pdf"
    _write_pdf(valid_pdf, "valid")

    report = run_corpus(
        [missing_pdf, valid_pdf],
        tmp_path / "artifacts",
        config=ExtractionConfig(overwrite=True),
    )

    assert report.succeeded == 1
    assert report.failed == 1
    failed_case = next(case for case in report.cases if case.status == "failed")
    assert failed_case.error_type == "FileNotFoundError"
    assert failed_case.performance is not None
    assert failed_case.performance.pages_per_second == 0.0

    report_path = write_corpus_report(report, tmp_path / "reports" / "benchmark.json")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["summary"] == {"failed": 1, "succeeded": 1, "total": 2}
    assert len(payload["cases"]) == 2
    assert "performance" in payload["cases"][0]


def test_measure_artifact_accepts_builder_output(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _write_pdf(pdf_path, "metrics")
    report = run_corpus([pdf_path], tmp_path / "out", config=ExtractionConfig(overwrite=True))
    artifact_metrics = report.cases[0].metrics

    assert artifact_metrics is not None
    assert artifact_metrics.source_sha256
    assert artifact_metrics.semantic_role_counts


def test_run_corpus_records_actionable_performance_metrics(tmp_path: Path) -> None:
    pdf_path = tmp_path / "performance.pdf"
    _write_pdf(pdf_path, "performance evidence")

    case = run_corpus(
        [pdf_path],
        tmp_path / "artifacts",
        config=ExtractionConfig(overwrite=True),
    ).cases[0]

    assert case.performance is not None
    assert case.performance.source_size_bytes == pdf_path.stat().st_size
    assert case.performance.output_size_bytes > 0
    assert case.performance.peak_python_memory_bytes > 0
    assert case.performance.pages_per_second > 0
    assert case.performance.source_mib_per_second > 0
    assert case.performance.output_to_source_ratio > 0
    assert case.performance.cache_hit is False


def test_run_corpus_preserves_existing_tracemalloc_session(tmp_path: Path) -> None:
    import tracemalloc

    pdf_path = tmp_path / "tracing.pdf"
    _write_pdf(pdf_path, "tracing")
    tracemalloc.start()
    try:
        run_corpus([pdf_path], tmp_path / "artifacts", config=ExtractionConfig(overwrite=True))
        assert tracemalloc.is_tracing()
    finally:
        tracemalloc.stop()


def test_run_corpus_reuses_matching_completed_artifact(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cached.pdf"
    output_root = tmp_path / "artifacts"
    _write_pdf(pdf_path, "cache me")

    first = run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True)).cases[0]
    second = run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True)).cases[0]

    assert first.performance is not None
    assert second.performance is not None
    assert first.performance.cache_hit is False
    assert second.performance.cache_hit is True
    assert second.performance.peak_python_memory_bytes == 0
    assert second.metrics == first.metrics
    assert (Path(second.output_dir) / ".akilan-benchmark-cache.json").is_file()


def test_run_corpus_invalidates_cache_when_source_changes(tmp_path: Path) -> None:
    pdf_path = tmp_path / "changed.pdf"
    output_root = tmp_path / "artifacts"
    _write_pdf(pdf_path, "first content")
    first = run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True)).cases[0]

    _write_pdf(pdf_path, "replacement content")
    second = run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True)).cases[0]

    assert first.metrics is not None
    assert second.metrics is not None
    assert second.performance is not None
    assert second.performance.cache_hit is False
    assert second.metrics.source_sha256 != first.metrics.source_sha256


def test_run_corpus_invalidates_cache_when_configuration_changes(tmp_path: Path) -> None:
    pdf_path = tmp_path / "configuration.pdf"
    output_root = tmp_path / "artifacts"
    _write_pdf(pdf_path, "configuration")
    run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True, include_plain_text=True))

    second = run_corpus(
        [pdf_path],
        output_root,
        config=ExtractionConfig(overwrite=True, include_plain_text=False),
    ).cases[0]

    assert second.performance is not None
    assert second.performance.cache_hit is False


def test_run_corpus_ignores_corrupt_cache_marker(tmp_path: Path) -> None:
    pdf_path = tmp_path / "corrupt.pdf"
    output_root = tmp_path / "artifacts"
    _write_pdf(pdf_path, "corrupt cache")
    first = run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True)).cases[0]
    marker = Path(first.output_dir) / ".akilan-benchmark-cache.json"
    marker.write_text("not-json", encoding="utf-8")

    second = run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True)).cases[0]

    assert second.performance is not None
    assert second.performance.cache_hit is False
    assert second.status == "passed"


def test_run_corpus_can_force_rebuild(tmp_path: Path) -> None:
    pdf_path = tmp_path / "forced.pdf"
    output_root = tmp_path / "artifacts"
    _write_pdf(pdf_path, "force rebuild")
    run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True))

    second = run_corpus(
        [pdf_path],
        output_root,
        config=ExtractionConfig(overwrite=True),
        use_cache=False,
    ).cases[0]

    assert second.performance is not None
    assert second.performance.cache_hit is False
