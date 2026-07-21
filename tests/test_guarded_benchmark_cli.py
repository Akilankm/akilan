from __future__ import annotations

import json
from pathlib import Path

import fitz

from akilan.guarded_benchmark_cli import main


def _write_pdf(path: Path, text: str = "Guarded benchmark evidence") -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_guarded_benchmark_cli_accepts_ready_corpus(tmp_path: Path, capsys: object) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_pdf(corpus / "ready.pdf")
    output_root = tmp_path / "artifacts"
    report = tmp_path / "report.json"
    acceptance = tmp_path / "acceptance.json"

    exit_code = main(
        [
            str(corpus),
            "--output-root",
            str(output_root),
            "--report",
            str(report),
            "--acceptance-report",
            str(acceptance),
            "--min-ordered-element-ratio",
            "0",
            "--no-cache",
        ]
    )

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["accepted"] is True
    assert payload["succeeded"] == 1
    assert payload["failed"] == 0
    assert report.is_file()
    assert acceptance.is_file()
    assert output_root.is_dir()


def test_guarded_benchmark_cli_rejects_before_output_creation(tmp_path: Path, capsys: object) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "broken.pdf").write_bytes(b"not a PDF")
    output_root = tmp_path / "artifacts"
    report = tmp_path / "report.json"
    guard_report = tmp_path / "guard.json"

    exit_code = main(
        [
            str(corpus),
            "--output-root",
            str(output_root),
            "--report",
            str(report),
            "--guard-report",
            str(guard_report),
        ]
    )

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.err)
    persisted = json.loads(guard_report.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["accepted"] is False
    assert payload["rejected_count"] == 1
    assert persisted["rejected_count"] == 1
    assert not output_root.exists()
    assert not report.exists()


def test_guarded_benchmark_cli_rejects_empty_corpus_without_side_effects(
    tmp_path: Path,
    capsys: object,
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    output_root = tmp_path / "artifacts"
    report = tmp_path / "report.json"

    exit_code = main(
        [
            str(corpus),
            "--output-root",
            str(output_root),
            "--report",
            str(report),
        ]
    )

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.err)
    assert exit_code == 1
    assert payload["accepted"] is False
    assert payload["total_count"] == 0
    assert not output_root.exists()
    assert not report.exists()
