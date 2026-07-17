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

    report_path = write_corpus_report(report, tmp_path / "reports" / "benchmark.json")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["summary"] == {"failed": 1, "succeeded": 1, "total": 2}
    assert len(payload["cases"]) == 2


def test_measure_artifact_accepts_builder_output(tmp_path: Path) -> None:
    pdf_path = tmp_path / "document.pdf"
    _write_pdf(pdf_path, "metrics")
    report = run_corpus([pdf_path], tmp_path / "out", config=ExtractionConfig(overwrite=True))
    artifact_metrics = report.cases[0].metrics

    assert artifact_metrics is not None
    assert artifact_metrics.source_sha256
    assert artifact_metrics.semantic_role_counts
