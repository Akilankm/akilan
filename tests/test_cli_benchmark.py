from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from akilan.cli import main


def _write_pdf(path: Path, text: str = "benchmark fixture") -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_benchmark_command_writes_report_and_succeeds(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    corpus = tmp_path / "data"
    corpus.mkdir()
    _write_pdf(corpus / "sample.pdf")
    output_root = tmp_path / "artifacts"
    report_path = tmp_path / "reports" / "benchmark.json"

    exit_code = main(
        [
            "benchmark",
            str(corpus),
            "--output-root",
            str(output_root),
            "--report",
            str(report_path),
            "--no-cache",
        ]
    )

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["total"] == 1
    assert summary["succeeded"] == 1
    assert summary["failed"] == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"] == {"failed": 0, "succeeded": 1, "total": 1}


def test_benchmark_command_returns_nonzero_when_a_case_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = tmp_path / "data"
    corpus.mkdir()
    (corpus / "broken.pdf").write_bytes(b"not a PDF")
    report_path = tmp_path / "benchmark.json"

    exit_code = main(
        [
            "benchmark",
            str(corpus),
            "--output-root",
            str(tmp_path / "artifacts"),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 1
    summary = json.loads(capsys.readouterr().out)
    assert summary["failed"] == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["cases"][0]["status"] == "failed"
    assert report["cases"][0]["error_type"]


def test_benchmark_command_rejects_empty_corpus(tmp_path: Path) -> None:
    corpus = tmp_path / "data"
    corpus.mkdir()

    with pytest.raises(SystemExit, match="no benchmark PDFs matched"):
        main(
            [
                "benchmark",
                str(corpus),
                "--output-root",
                str(tmp_path / "artifacts"),
                "--report",
                str(tmp_path / "benchmark.json"),
            ]
        )
