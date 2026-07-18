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
