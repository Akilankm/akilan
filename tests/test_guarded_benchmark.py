from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from akilan.config import ExtractionConfig
from akilan.guarded_benchmark import BenchmarkSourceGuardError, run_guarded_corpus


def _write_pdf(path: Path, text: str) -> None:
    document = pymupdf.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((30, 40), text)
    document.save(path)
    document.close()


def test_run_guarded_corpus_extracts_only_after_all_sources_pass_preflight(tmp_path: Path) -> None:
    second = tmp_path / "b.pdf"
    first = tmp_path / "a.pdf"
    _write_pdf(second, "second")
    _write_pdf(first, "first")
    output_root = tmp_path / "artifacts"

    report = run_guarded_corpus(
        (path for path in [second, first]),
        output_root,
        config=ExtractionConfig(overwrite=True),
        use_cache=False,
    )

    assert report.succeeded == 2
    assert report.failed == 0
    assert [Path(case.source).name for case in report.cases] == ["a.pdf", "b.pdf"]
    assert output_root.is_dir()


def test_run_guarded_corpus_rejects_exact_set_before_creating_output(tmp_path: Path) -> None:
    valid_pdf = tmp_path / "valid.pdf"
    missing_pdf = tmp_path / "missing.pdf"
    output_root = tmp_path / "artifacts"
    _write_pdf(valid_pdf, "valid")

    with pytest.raises(BenchmarkSourceGuardError) as captured:
        run_guarded_corpus(
            [valid_pdf, missing_pdf],
            output_root,
            config=ExtractionConfig(overwrite=True),
        )

    report = captured.value.report
    assert report.accepted is False
    assert report.total_count == 2
    assert report.accepted_count == 1
    assert report.rejected_count == 1
    assert report.status_counts == {"missing": 1, "ready": 1}
    assert not output_root.exists()


def test_run_guarded_corpus_rejects_empty_source_set_without_side_effects(tmp_path: Path) -> None:
    output_root = tmp_path / "artifacts"

    with pytest.raises(BenchmarkSourceGuardError) as captured:
        run_guarded_corpus([], output_root)

    assert captured.value.report.total_count == 0
    assert captured.value.report.entries == ()
    assert not output_root.exists()
