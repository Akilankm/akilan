from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from akilan.pdf_preflight_cli import main


def _write_pdf(path: Path) -> None:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "CLI preflight evidence")
    document.save(path)
    document.close()


def _write_encrypted_pdf(path: Path, password: str) -> None:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Encrypted CLI evidence")
    document.save(
        path,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="fixture-owner-password",
        user_pw=password,
    )
    document.close()


def test_preflight_cli_accepts_pdf_and_persists_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "valid.pdf"
    report_path = tmp_path / "reports" / "preflight.json"
    _write_pdf(source)

    exit_code = main([str(source), "--report", str(report_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert captured.err == ""
    assert payload["accepted"] is True
    assert payload["status"] == "ready"
    assert payload["page_count"] == 1
    assert payload["report"] == str(report_path.resolve())
    assert persisted["status"] == "ready"
    assert "accepted" not in persisted


def test_preflight_cli_fails_closed_on_missing_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "missing.pdf"

    exit_code = main([str(source)])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exit_code == 1
    assert captured.out == ""
    assert payload["accepted"] is False
    assert payload["status"] == "missing"


def test_preflight_cli_reads_password_from_file_without_exposing_it(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "encrypted.pdf"
    password_file = tmp_path / "password.txt"
    password = "fixture-user-password"
    _write_encrypted_pdf(source, password)
    password_file.write_text(f"{password}\n", encoding="utf-8")

    exit_code = main([str(source), "--password-file", str(password_file)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["status"] == "ready"
    assert password not in captured.out
