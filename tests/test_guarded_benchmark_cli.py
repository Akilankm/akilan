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
    guard_report = tmp_path / "guard.json"
    performance_report = tmp_path / "performance.json"
    execution_identity_report = tmp_path / "execution-identity.json"

    exit_code = main(
        [
            str(corpus),
            "--output-root",
            str(output_root),
            "--report",
            str(report),
            "--acceptance-report",
            str(acceptance),
            "--guard-report",
            str(guard_report),
            "--performance-report",
            str(performance_report),
            "--execution-identity-report",
            str(execution_identity_report),
            "--min-ordered-element-ratio",
            "0",
            "--no-cache",
        ]
    )

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)
    persisted_guard = json.loads(guard_report.read_text(encoding="utf-8"))
    persisted_performance = json.loads(performance_report.read_text(encoding="utf-8"))
    persisted_identity = json.loads(execution_identity_report.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["accepted"] is True
    assert payload["succeeded"] == 1
    assert payload["failed"] == 0
    assert payload["guard_report"] == str(guard_report.resolve())
    assert payload["performance_report"] == str(performance_report.resolve())
    assert payload["execution_identity_report"] == str(execution_identity_report.resolve())
    assert payload["guarded_source_count"] == 1
    assert payload["guard_fingerprint"] == persisted_guard["fingerprint"]
    assert payload["performance"] == persisted_performance
    assert payload["execution_identity"] == persisted_identity
    assert payload["execution_identity_fingerprint"] == persisted_identity["fingerprint"]
    assert persisted_identity["valid"] is True
    assert len(persisted_identity["fingerprint"]) == 64
    assert persisted_identity["extraction_config"]["overwrite"] is True
    assert persisted_identity["extraction_config"]["render_pages"] is False
    assert persisted_performance["measured_case_count"] == 1
    assert persisted_performance["total_page_count"] == 1
    assert persisted_performance["total_source_size_bytes"] > 0
    assert persisted_performance["total_output_size_bytes"] > 0
    assert persisted_performance["total_elapsed_seconds"] >= 0
    assert persisted_performance["pages_per_second"] >= 0
    assert persisted_performance["source_mib_per_second"] >= 0
    assert persisted_performance["peak_python_memory_bytes"] >= 0
    assert isinstance(persisted_performance["phase_seconds"], dict)
    assert all(value >= 0 for value in persisted_performance["phase_seconds"].values())
    assert persisted_guard["accepted_count"] == 1
    assert persisted_guard["rejected_count"] == 0
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
    performance_report = tmp_path / "performance.json"
    execution_identity_report = tmp_path / "execution-identity.json"

    exit_code = main(
        [
            str(corpus),
            "--output-root",
            str(output_root),
            "--report",
            str(report),
            "--guard-report",
            str(guard_report),
            "--performance-report",
            str(performance_report),
            "--execution-identity-report",
            str(execution_identity_report),
        ]
    )

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.err)
    persisted = json.loads(guard_report.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["accepted"] is False
    assert payload["rejected_count"] == 1
    assert payload["performance_report"] is None
    assert payload["execution_identity_report"] is None
    assert persisted["rejected_count"] == 1
    assert not output_root.exists()
    assert not report.exists()
    assert not performance_report.exists()
    assert not execution_identity_report.exists()


def test_guarded_benchmark_cli_rejects_empty_corpus_without_side_effects(
    tmp_path: Path,
    capsys: object,
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    output_root = tmp_path / "artifacts"
    report = tmp_path / "report.json"
    performance_report = tmp_path / "performance.json"
    execution_identity_report = tmp_path / "execution-identity.json"

    exit_code = main(
        [
            str(corpus),
            "--output-root",
            str(output_root),
            "--report",
            str(report),
            "--performance-report",
            str(performance_report),
            "--execution-identity-report",
            str(execution_identity_report),
        ]
    )

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.err)
    assert exit_code == 1
    assert payload["accepted"] is False
    assert payload["total_count"] == 0
    assert payload["performance_report"] is None
    assert payload["execution_identity_report"] is None
    assert not output_root.exists()
    assert not report.exists()
    assert not performance_report.exists()
    assert not execution_identity_report.exists()
