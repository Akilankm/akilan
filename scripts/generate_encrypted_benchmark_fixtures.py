#!/usr/bin/env python3
"""Generate a copyright-free encrypted PDF fixture for extraction regression tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf

_OWNER_PASSWORD = "akilan-owner"
_USER_PASSWORD = "akilan-user"
_PAGE = pymupdf.paper_rect("a4")


def _new_document() -> pymupdf.Document:
    document = pymupdf.open()
    document.set_metadata(
        {
            "author": "AKILAN",
            "creator": "AKILAN encrypted benchmark fixture generator",
            "producer": "PyMuPDF",
            "subject": "Generated encrypted PDF regression fixture",
            "title": "AKILAN Benchmark: Encrypted User Password",
        }
    )
    page = document.new_page(width=_PAGE.width, height=_PAGE.height)
    page.insert_text((72, 72), "AKILAN Benchmark: Encrypted User Password", fontsize=18)
    page.insert_textbox(
        pymupdf.Rect(72, 105, 520, 260),
        "This generated document validates explicit encrypted-PDF handling, password rejection, "
        "successful authentication, and artifact publication without third-party source material.\n\n"
        "The fixture password is intentionally public test data and must never be reused for real documents.",
        fontsize=11,
        lineheight=1.25,
    )
    page.draw_rect(pymupdf.Rect(72, 300, 520, 390), width=1)
    page.insert_text((92, 342), "Encrypted evidence generated locally with PyMuPDF.", fontsize=11)
    return document


def generate_fixture(output_dir: Path) -> dict[str, object]:
    """Generate one password-required fixture and return credential-free evidence."""

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "encrypted_user_password.pdf"
    document = _new_document()
    document.save(
        path,
        garbage=4,
        deflate=True,
        clean=True,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw=_OWNER_PASSWORD,
        user_pw=_USER_PASSWORD,
        permissions=pymupdf.PDF_PERM_ACCESSIBILITY | pymupdf.PDF_PERM_PRINT,
    )
    document.close()

    with pymupdf.open(path) as reopened:
        case = {
            "case_id": "user_password",
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "is_pdf": bool(reopened.is_pdf),
            "is_encrypted": bool(reopened.is_encrypted),
            "needs_password": bool(reopened.needs_pass),
            "page_count_available_before_authentication": reopened.page_count,
        }

    return {
        "output_dir": str(output_dir),
        "case_count": 1,
        "cases": [case],
        "credential_values_included": False,
        "production_use_forbidden": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--evidence", type=Path, help="Optional JSON evidence output path")
    args = parser.parse_args(argv)

    payload = generate_fixture(args.output_dir)
    if args.evidence is not None:
        evidence_path = args.evidence.expanduser().resolve()
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload = {**payload, "evidence": str(evidence_path)}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
