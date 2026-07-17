"""Shared native PyMuPDF helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pymupdf


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in "._-" else "_" for character in value)
    return cleaned.strip("._") or "asset"


def text_flags() -> int:
    names = (
        "TEXT_PRESERVE_LIGATURES",
        "TEXT_PRESERVE_WHITESPACE",
        "TEXT_MEDIABOX_CLIP",
        "TEXT_CID_FOR_UNKNOWN_UNICODE",
    )
    flags = 0
    for name in names:
        flags |= int(getattr(pymupdf, name, 0))
    return flags


def span_text(span: dict[str, Any]) -> str:
    if "text" in span:
        return str(span.get("text") or "")
    return "".join(str(char.get("c") or "") for char in span.get("chars", []))


def point(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
    try:
        parsed = pymupdf.Point(value)
        return (round(float(parsed.x), 4), round(float(parsed.y), 4))
    except Exception:
        return None


def table_markdown(rows: list[list[str | None]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    normalized = [
        [(cell or "").replace("\n", " ").replace("|", "\\|") for cell in row] + [""] * (width - len(row))
        for row in rows
    ]
    header = normalized[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    return "\n".join(lines)
