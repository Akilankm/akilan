#!/usr/bin/env python3
"""Generate copyright-free encrypted PDF fixtures for extraction regression tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf

_OWNER_PASSWORD = "akilan-owner"
_USER_PASSWORD = "akilan-user"
_PAGE = pymupdf.paper_rect("a4")


def _new_document(title: str) -> pymupdf.Document:
    document = pymupdf.open()
    document.set_metadata(
        {
            "author": "AKILAN",
            "creator": "AKILAN encrypted benchmark fixture generator",
            "producer": "PyMuPDF",
            "subject": "Generated encrypted PDF regression fixture",
            "title": title,
        }
    )
    page = document.new_page(width=_PAGE.width, height=_PAGE.height)
    page.insert_text((72, 72), title, fontsize=18)
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


def _save_encrypted(document: pymupdf.Document, path: Path, *, user_password: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(
        path,
        garbage=4,
        deflate=True,
        clean=True,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw=_OWNER_PASSWORD,
        user_pw=user_password,
        permissions=pymupdf.PDF_PERM_ACCESSIBILITY | pymupdf.PDF_PERM_PRINT,
    )
    document.close()


def generate_fixtures(output_dir: Path) -> dict[str, object]:
    """Generate encrypted fixtures and return non-secret machine-readable evidence."""

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = (
        ("owner_only", output_dir / "encrypted_owner_only.pdf", ""),
        ("user_password", output_dir / "encrypted_user_password.pdf", _USER_PASSWORD),
    )

    evidence: list[dict[str, object]] = []
    for case_id, path, user_password in cases:
        document = _new_document(f"AKILAN Benchmark: Encrypted {case_id.replace('_', ' ').title()}")
        _save_encrypted(document, path, user_password=user_password)
        with pymupdf.open(path) as reopened:
            evidence.append(
                {
                    "case_id": case_id,
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "is_pdf": bool(reopened.is_pdf),
                    "is_encrypted": bool(reopened.is_encrypted),
                    "needs_password": bool(reopened.needs_pass),
                    "page_count_available_before_authentication": reopened.page_count,
                }
            )

    return {
        "output_dir": str(output_dir),
        "case_count": len(evidence),
        "cases": evidence,
        "test_password_contract": {
            "owner_password": _OWNER_PASSWORD,
            "user_password": _USER_PASSWORD,
            "production_use_forbidden": True,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--evidence", type=Path, help="Optional JSON evidence output path")
    args = parser.parse_args(argv)

    payload = generate_fixtures(args.output_dir)
    if args.evidence is not None:
        evidence_path = args.evidence.expanduser().resolve()
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload = {**payload, "evidence": str(evidence_path)}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
