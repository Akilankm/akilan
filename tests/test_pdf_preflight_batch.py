from __future__ import annotations

from pathlib import Path

import pymupdf

from akilan.pdf_preflight_batch import preflight_pdf_batch


def _write_pdf(path: Path, text: str) -> None:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_batch_preflight_is_stable_and_accepts_valid_corpus(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    _write_pdf(tmp_path / "b.pdf", "B")
    _write_pdf(nested / "a.pdf", "A")

    first = preflight_pdf_batch(tmp_path)
    second = preflight_pdf_batch(tmp_path)

    assert first.accepted is True
    assert first.total_count == 2
    assert first.status_counts == {"ready": 2}
    assert [Path(entry.source_path).name for entry in first.entries] == ["b.pdf", "a.pdf"]
    assert first.fingerprint == second.fingerprint


def test_batch_preflight_fails_closed_for_empty_or_rejected_corpus(tmp_path: Path) -> None:
    empty = preflight_pdf_batch(tmp_path)
    assert empty.accepted is False
    assert empty.total_count == 0

    (tmp_path / "broken.pdf").write_bytes(b"not a PDF")
    rejected = preflight_pdf_batch(tmp_path)

    assert rejected.accepted is False
    assert rejected.rejected_count == 1
    assert rejected.status_counts == {"unreadable_pdf": 1}


def test_batch_preflight_passwords_are_not_persisted(tmp_path: Path) -> None:
    source = tmp_path / "encrypted.pdf"
    password = "batch-secret"
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Encrypted")
    document.save(
        source,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw=password,
    )
    document.close()

    report = preflight_pdf_batch(tmp_path, passwords={"encrypted.pdf": password})
    payload = report.to_dict()

    assert report.accepted is True
    assert password not in str(payload)
    assert "owner-secret" not in str(payload)
