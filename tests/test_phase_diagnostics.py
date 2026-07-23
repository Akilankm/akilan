from __future__ import annotations

from pathlib import Path

import pymupdf

from akilan.benchmark import run_corpus
from akilan.config import ExtractionConfig


def _write_pdf(path: Path, text: str) -> None:
    document = pymupdf.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((30, 40), text)
    document.save(path)
    document.close()


def test_cold_run_records_named_phases(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cold.pdf"
    _write_pdf(pdf_path, "phase diagnostics")

    case = run_corpus(
        [pdf_path],
        tmp_path / "artifacts",
        config=ExtractionConfig(overwrite=True),
        use_cache=False,
    ).cases[0]

    assert case.performance is not None
    phases = case.performance.phase_seconds
    assert set(phases) == {"cache_lookup", "extraction", "measurement", "total"}
    assert all(duration >= 0 for duration in phases.values())
    assert phases["total"] == case.elapsed_seconds
    assert phases["total"] >= phases["extraction"]


def test_cached_run_reports_lookup_without_fake_extraction(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cached.pdf"
    output_root = tmp_path / "artifacts"
    _write_pdf(pdf_path, "cache diagnostics")

    run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True))
    cached = run_corpus([pdf_path], output_root, config=ExtractionConfig(overwrite=True)).cases[0]

    assert cached.performance is not None
    assert cached.performance.cache_hit is True
    assert set(cached.performance.phase_seconds) == {"cache_lookup", "total"}
    assert cached.performance.phase_seconds["total"] == cached.elapsed_seconds


def test_failed_run_retains_phase_evidence(tmp_path: Path) -> None:
    missing = tmp_path / "missing.pdf"

    case = run_corpus(
        [missing],
        tmp_path / "artifacts",
        config=ExtractionConfig(overwrite=True),
    ).cases[0]

    assert case.status == "failed"
    assert case.performance is not None
    assert case.performance.phase_seconds["total"] == case.elapsed_seconds
    assert "cache_lookup" in case.performance.phase_seconds
    assert "extraction" in case.performance.phase_seconds
