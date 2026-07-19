from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from akilan.cli import main


def _write_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "AKILAN benchmark acceptance fixture")
    document.save(path)
    document.close()


def test_benchmark_cli_writes_passing_acceptance_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_pdf(corpus / "simple.pdf")
    report = tmp_path / "reports" / "corpus.json"
    acceptance_report = tmp_path / "reports" / "acceptance.json"

    exit_code = main(
        [
            "benchmark",
            str(corpus),
            "--output-root",
            str(tmp_path / "artifacts"),
            "--report",
            str(report),
            "--acceptance-report",
            str(acceptance_report),
            "--no-cache",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    acceptance = json.loads(acceptance_report.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["accepted"] is True
    assert payload["violation_count"] == 0
    assert acceptance["passed"] is True
    assert report.is_file()


def test_benchmark_cli_fails_when_threshold_is_violated(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_pdf(corpus / "simple.pdf")

    exit_code = main(
        [
            "benchmark",
            str(corpus),
            "--output-root",
            str(tmp_path / "artifacts"),
            "--report",
            str(tmp_path / "corpus.json"),
            "--max-output-to-source-ratio",
            "0",
            "--no-cache",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["accepted"] is False
    assert payload["violation_count"] == 1
    assert payload["violations"][0]["metric"] == "output_to_source_ratio"


def test_benchmark_cli_rejects_invalid_threshold_before_extraction(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_pdf(corpus / "simple.pdf")

    with pytest.raises(SystemExit, match="invalid benchmark threshold"):
        main(
            [
                "benchmark",
                str(corpus),
                "--output-root",
                str(tmp_path / "artifacts"),
                "--report",
                str(tmp_path / "corpus.json"),
                "--min-success-rate",
                "1.1",
            ]
        )

    assert not (tmp_path / "artifacts").exists()
    assert capsys.readouterr().out == ""
