from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from akilan.pdf_preflight_batch_cli import main


def _write_pdf(path: Path, text: str) -> None:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_batch_preflight_cli_accepts_valid_corpus_and_writes_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_pdf(tmp_path / "a.pdf", "A")
    report_path = tmp_path / "reports" / "preflight.json"

    exit_code = main([str(tmp_path), "--report", str(report_path)])

    assert exit_code == 0
    assert capsys.readouterr().err == ""
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["accepted"] is True
    assert payload["total_count"] == 1
    assert payload["status_counts"] == {"ready": 1}


def test_batch_preflight_cli_fails_closed_for_empty_corpus(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["accepted"] is False
    assert payload["total_count"] == 0


def test_batch_preflight_cli_respects_non_recursive_discovery(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    _write_pdf(nested / "nested.pdf", "Nested")

    exit_code = main([str(tmp_path), "--no-recursive"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["recursive"] is False
    assert payload["total_count"] == 0


def test_batch_preflight_cli_authenticates_without_disclosing_passwords(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "encrypted.pdf"
    password = "batch-cli-secret"
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Encrypted")
    document.save(
        source,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw=password,
    )
    document.close()
    password_map = tmp_path / "passwords.json"
    password_map.write_text(json.dumps({"encrypted.pdf": password}), encoding="utf-8")

    exit_code = main([str(tmp_path), "--password-map", str(password_map)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert password not in captured.out
    assert "owner-secret" not in captured.out


def test_batch_preflight_cli_rejects_invalid_password_map(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    password_map = tmp_path / "passwords.json"
    password_map.write_text("[]", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path), "--password-map", str(password_map)])

    assert exc_info.value.code == 2
    assert "password map must be a JSON object" in capsys.readouterr().err
