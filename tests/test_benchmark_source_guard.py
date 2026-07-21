from __future__ import annotations

from pathlib import Path

import fitz

from akilan.benchmark_source_guard import guard_benchmark_sources


def _write_pdf(path: Path, text: str) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_guard_accepts_and_orders_exact_sources(tmp_path: Path) -> None:
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    _write_pdf(first, "first")
    _write_pdf(second, "second")

    report = guard_benchmark_sources([second, first, second])

    assert report.accepted is True
    assert report.total_count == 2
    assert report.accepted_count == 2
    assert report.rejected_count == 0
    assert report.status_counts == {"ready": 2}
    assert [entry.source_path for entry in report.entries] == [str(first.resolve()), str(second.resolve())]
    assert report.fingerprint == guard_benchmark_sources([first, second]).fingerprint


def test_guard_fails_closed_for_invalid_and_missing_sources(tmp_path: Path) -> None:
    invalid = tmp_path / "broken.pdf"
    missing = tmp_path / "missing.pdf"
    invalid.write_bytes(b"not a PDF")

    report = guard_benchmark_sources([missing, invalid])

    assert report.accepted is False
    assert report.total_count == 2
    assert report.accepted_count == 0
    assert report.rejected_count == 2
    assert report.status_counts == {"missing": 1, "unreadable_pdf": 1}


def test_guard_fails_closed_for_empty_source_set() -> None:
    report = guard_benchmark_sources([])

    assert report.accepted is False
    assert report.total_count == 0
    assert report.entries == ()
    assert report.status_counts == {}


def test_guard_uses_password_without_persisting_it(tmp_path: Path) -> None:
    source = tmp_path / "encrypted.pdf"
    password = "fixture-secret"
    document = fitz.open()
    document.new_page().insert_text((72, 72), "encrypted benchmark")
    document.save(
        source,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw=password,
    )
    document.close()

    report = guard_benchmark_sources([source], passwords={str(source): password})
    payload = report.to_dict()

    assert report.accepted is True
    assert report.status_counts == {"ready": 1}
    assert password not in str(payload)
    assert "owner-secret" not in str(payload)
