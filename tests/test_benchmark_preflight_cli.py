from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from akilan.benchmark_preflight_cli import main


def _write_pdf(path: Path, text: str = "benchmark preflight fixture") -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def _write_encrypted_pdf(path: Path, password: str) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "encrypted benchmark preflight fixture")
    document.save(
        path,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="benchmark-owner-password",
        user_pw=password,
    )
    document.close()


def test_benchmark_preflight_accepts_valid_corpus_and_writes_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_pdf(corpus / "b.pdf")
    _write_pdf(corpus / "a.pdf")
    report_path = tmp_path / "reports" / "preflight.json"

    exit_code = main([str(corpus), "--report", str(report_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["accepted"] is True
    assert payload["total_count"] == 2
    assert payload["accepted_count"] == 2
    assert payload["rejected_count"] == 0
    assert [Path(entry["source_path"]).name for entry in payload["entries"]] == ["a.pdf", "b.pdf"]
    assert payload["fingerprint"]
    assert json.loads(report_path.read_text(encoding="utf-8"))["accepted"] is True


def test_benchmark_preflight_rejects_invalid_pdf_without_creating_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "broken.pdf").write_bytes(b"not a PDF")

    exit_code = main([str(corpus)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["accepted"] is False
    assert payload["rejected_count"] == 1
    assert payload["entries"][0]["status"] in {"not_pdf", "unreadable_pdf"}
    assert not (tmp_path / "artifacts").exists()


def test_benchmark_preflight_authenticates_encrypted_pdf_from_relative_password_map(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = tmp_path / "corpus"
    nested = corpus / "protected"
    nested.mkdir(parents=True)
    source = nested / "encrypted.pdf"
    password = "benchmark-user-password"
    _write_encrypted_pdf(source, password)
    password_map = tmp_path / "passwords.json"
    password_map.write_text(
        json.dumps({"protected/encrypted.pdf": password}),
        encoding="utf-8",
    )

    exit_code = main([str(corpus), "--password-map", str(password_map)])

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["accepted"] is True
    assert payload["entries"][0]["status"] == "ready"
    assert password not in output


def test_benchmark_preflight_rejects_encrypted_pdf_without_password(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_encrypted_pdf(corpus / "encrypted.pdf", "benchmark-user-password")

    exit_code = main([str(corpus)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["entries"][0]["status"] == "password_required"


def test_benchmark_preflight_rejects_malformed_password_map(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_pdf(corpus / "valid.pdf")
    password_map = tmp_path / "passwords.json"
    password_map.write_text("[]", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main([str(corpus), "--password-map", str(password_map)])

    assert exc_info.value.code == 2


def test_benchmark_preflight_fails_closed_for_empty_corpus(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()

    exit_code = main([str(corpus)])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["accepted"] is False
    assert payload["total_count"] == 0


def test_benchmark_preflight_rejects_missing_corpus(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "missing")])

    assert exc_info.value.code == 2
