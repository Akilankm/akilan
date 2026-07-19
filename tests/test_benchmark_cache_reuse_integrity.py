from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from akilan.benchmark import run_corpus
from akilan.config import ExtractionConfig


def _write_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((30, 40), "benchmark cache reuse integrity")
    document.save(path)
    document.close()


def _build_once(tmp_path: Path) -> tuple[Path, Path]:
    pdf_path = tmp_path / "source.pdf"
    output_root = tmp_path / "artifacts"
    _write_pdf(pdf_path)
    case = run_corpus(
        [pdf_path],
        output_root,
        config=ExtractionConfig(overwrite=True),
    ).cases[0]
    assert case.status == "passed"
    return pdf_path, Path(case.output_dir)


def test_run_corpus_rebuilds_when_cached_artifact_is_incomplete(tmp_path: Path) -> None:
    pdf_path, artifact_dir = _build_once(tmp_path)
    (artifact_dir / "document.json").unlink()

    case = run_corpus(
        [pdf_path],
        tmp_path / "artifacts",
        config=ExtractionConfig(overwrite=True),
    ).cases[0]

    assert case.status == "passed"
    assert case.performance is not None
    assert case.performance.cache_hit is False
    assert (artifact_dir / "document.json").is_file()


def test_run_corpus_rebuilds_when_cached_metrics_disagree_with_artifact(tmp_path: Path) -> None:
    pdf_path, artifact_dir = _build_once(tmp_path)
    marker_path = artifact_dir / ".akilan-benchmark-cache.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["metrics"]["page_count"] = 999
    marker_path.write_text(
        json.dumps(marker, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    case = run_corpus(
        [pdf_path],
        tmp_path / "artifacts",
        config=ExtractionConfig(overwrite=True),
    ).cases[0]

    assert case.status == "passed"
    assert case.performance is not None
    assert case.performance.cache_hit is False
    assert case.metrics is not None
    assert case.metrics.page_count == 1


def test_run_corpus_reuses_only_fully_validated_cache(tmp_path: Path) -> None:
    pdf_path, _ = _build_once(tmp_path)

    case = run_corpus(
        [pdf_path],
        tmp_path / "artifacts",
        config=ExtractionConfig(overwrite=True),
    ).cases[0]

    assert case.status == "passed"
    assert case.performance is not None
    assert case.performance.cache_hit is True
