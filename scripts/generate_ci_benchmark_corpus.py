#!/usr/bin/env python3
"""Generate a small copyright-free PDF corpus for CI benchmark evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf

_PAGE = pymupdf.paper_rect("a4")
_METADATA = {
    "author": "AKILAN",
    "creator": "AKILAN CI benchmark corpus generator",
    "producer": "PyMuPDF",
    "subject": "Deterministic generated benchmark fixture",
}


def _new_document(title: str) -> pymupdf.Document:
    document = pymupdf.open()
    document.set_metadata({**_METADATA, "title": title})
    return document


def _save(document: pymupdf.Document, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path, garbage=4, deflate=True, clean=True)
    document.close()


def _write_single_column(path: Path) -> None:
    document = _new_document("Single-column generated fixture")
    page = document.new_page(width=_PAGE.width, height=_PAGE.height)
    page.insert_text((72, 72), "AKILAN Benchmark: Single Column", fontsize=18)
    page.insert_textbox(
        pymupdf.Rect(72, 105, 520, 300),
        "This generated document validates deterministic text extraction, geometry preservation, "
        "reading order, and artifact reporting without relying on third-party copyrighted PDFs.\n\n"
        "The second paragraph provides stable multi-line content for coverage measurements.",
        fontsize=11,
        lineheight=1.25,
    )
    page.draw_line((72, 330), (520, 330), width=1)
    page.insert_text((72, 360), "Footer evidence: generated locally in CI.", fontsize=9)
    _save(document, path)


def _write_mixed_layout(path: Path) -> None:
    document = _new_document("Mixed-layout generated fixture")
    page = document.new_page(width=_PAGE.width, height=_PAGE.height)
    page.insert_text((72, 65), "AKILAN Benchmark: Mixed Layout", fontsize=18)
    page.insert_textbox(
        pymupdf.Rect(72, 100, 285, 360),
        "LEFT COLUMN\n\nAlpha evidence remains in the left reading region.\n\n"
        "Beta evidence follows beneath it with stable geometry.",
        fontsize=10,
        lineheight=1.25,
    )
    page.insert_textbox(
        pymupdf.Rect(315, 100, 528, 360),
        "RIGHT COLUMN\n\nGamma evidence remains in the right reading region.\n\n"
        "Delta evidence follows beneath it with stable geometry.",
        fontsize=10,
        lineheight=1.25,
    )
    page.draw_line((300, 95), (300, 370), width=0.8)
    page.draw_rect(pymupdf.Rect(72, 410, 528, 520), width=1)
    page.insert_text((90, 445), "Spanning region below both columns", fontsize=12)
    page.insert_text((90, 475), "Vector and text evidence are intentionally combined.", fontsize=10)
    _save(document, path)


def _write_rotated_cropped(path: Path) -> None:
    """Write a page whose visible geometry differs from its media box."""

    document = _new_document("Rotated and cropped generated fixture")
    page = document.new_page(width=_PAGE.width, height=_PAGE.height)
    page.insert_text((72, 88), "AKILAN Benchmark: Rotated and Cropped", fontsize=17)
    page.insert_textbox(
        pymupdf.Rect(72, 125, 520, 330),
        "This page validates that extraction preserves media-box, crop-box, and rotation evidence.\n\n"
        "Visible content remains inside the deterministic crop region while the page is presented "
        "with a ninety-degree clockwise rotation.",
        fontsize=11,
        lineheight=1.25,
    )
    page.draw_rect(pymupdf.Rect(60, 60, 535, 760), width=1)
    page.set_cropbox(pymupdf.Rect(36, 54, _PAGE.width - 36, _PAGE.height - 54))
    page.set_rotation(90)
    _save(document, path)


def _page_evidence(page: pymupdf.Page) -> dict[str, object]:
    return {
        "page_number": page.number + 1,
        "rotation": page.rotation,
        "media_box": list(page.mediabox),
        "crop_box": list(page.cropbox),
    }


def generate_corpus(output_dir: Path) -> dict[str, object]:
    """Generate the deterministic CI corpus and return machine-readable evidence."""

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = {
        "mixed_layout": output_dir / "mixed_layout.pdf",
        "rotated_cropped": output_dir / "rotated_cropped.pdf",
        "single_column": output_dir / "single_column.pdf",
    }
    _write_single_column(cases["single_column"])
    _write_mixed_layout(cases["mixed_layout"])
    _write_rotated_cropped(cases["rotated_cropped"])

    evidence: list[dict[str, object]] = []
    for case_id, path in sorted(cases.items()):
        with pymupdf.open(path) as document:
            evidence.append(
                {
                    "case_id": case_id,
                    "path": str(path),
                    "page_count": document.page_count,
                    "size_bytes": path.stat().st_size,
                    "pages": [_page_evidence(page) for page in document],
                }
            )
    return {"output_dir": str(output_dir), "case_count": len(evidence), "cases": evidence}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--evidence", type=Path, help="Optional JSON evidence output path")
    args = parser.parse_args(argv)

    payload = generate_corpus(args.output_dir)
    if args.evidence is not None:
        evidence_path = args.evidence.expanduser().resolve()
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload = {**payload, "evidence": str(evidence_path)}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
