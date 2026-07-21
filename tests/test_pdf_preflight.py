from __future__ import annotations

from pathlib import Path

import pymupdf

from akilan.pdf_preflight import preflight_pdf


def _write_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Preflight evidence")
    document.save(path)
    document.close()


def _write_encrypted_pdf(path: Path, password: str) -> None:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Encrypted evidence")
    document.save(
        path,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="fixture-owner-password",
        user_pw=password,
    )
    document.close()


def test_preflight_accepts_readable_pdf(tmp_path: Path) -> None:
    source = tmp_path / "valid.pdf"
    _write_pdf(source)

    report = preflight_pdf(source)

    assert report.accepted is True
    assert report.status == "ready"
    assert report.page_count == 1
    assert report.is_pdf is True
    assert report.size_bytes == source.stat().st_size
    assert report.to_dict()["source_path"] == str(source.resolve())


def test_preflight_classifies_missing_empty_and_malformed_sources(tmp_path: Path) -> None:
    missing = preflight_pdf(tmp_path / "missing.pdf")
    assert missing.status == "missing"
    assert missing.accepted is False

    empty_path = tmp_path / "empty.pdf"
    empty_path.write_bytes(b"")
    empty = preflight_pdf(empty_path)
    assert empty.status == "empty_file"
    assert empty.size_bytes == 0

    malformed_path = tmp_path / "malformed.pdf"
    malformed_path.write_bytes(b"not a pdf")
    malformed = preflight_pdf(malformed_path)
    assert malformed.status == "unreadable_pdf"
    assert malformed.error_type == "FileDataError"


def test_preflight_classifies_encrypted_pdf_without_exposing_password(tmp_path: Path) -> None:
    source = tmp_path / "encrypted.pdf"
    password = "fixture-user-password"
    _write_encrypted_pdf(source, password)

    required = preflight_pdf(source)
    assert required.status == "password_required"
    assert required.is_encrypted is True

    invalid = preflight_pdf(source, password="wrong-password")
    assert invalid.status == "invalid_password"

    accepted = preflight_pdf(source, password=password)
    assert accepted.status == "ready"
    assert accepted.page_count == 1

    for report in (required, invalid, accepted):
        assert password not in str(report.to_dict())
        assert "wrong-password" not in str(report.to_dict())
