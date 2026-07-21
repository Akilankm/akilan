"""Deterministic, read-only preflight for a corpus of PDF sources."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .canonical_json import canonical_json_sha256
from .pdf_preflight import PDFPreflightReport, preflight_pdf


@dataclass(frozen=True, slots=True)
class PDFPreflightBatchReport:
    """Stable machine-readable evidence for a preflight corpus."""

    root_path: str
    recursive: bool
    total_count: int
    accepted_count: int
    rejected_count: int
    status_counts: dict[str, int]
    entries: tuple[PDFPreflightReport, ...]
    fingerprint: str

    @property
    def accepted(self) -> bool:
        return self.total_count > 0 and self.rejected_count == 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["accepted"] = self.accepted
        return payload


def _discover_sources(root: Path, *, recursive: bool) -> tuple[Path, ...]:
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return tuple(sorted((path.resolve() for path in root.glob(pattern) if path.is_file()), key=str))


def preflight_pdf_batch(
    root_path: str | Path,
    *,
    recursive: bool = True,
    passwords: dict[str, str] | None = None,
) -> PDFPreflightBatchReport:
    """Preflight every PDF below ``root_path`` without modifying source or artifact state.

    Password lookup keys may be absolute normalized paths or paths relative to the root.
    Password values are passed directly to ``preflight_pdf`` and are never persisted.
    """

    root = Path(root_path).expanduser().resolve()
    sources = _discover_sources(root, recursive=recursive) if root.is_dir() else ()
    password_map = passwords or {}
    entries: list[PDFPreflightReport] = []
    for source in sources:
        relative_key = source.relative_to(root).as_posix()
        password = password_map.get(str(source), password_map.get(relative_key))
        entries.append(preflight_pdf(source, password=password))

    status_counts = dict(sorted(Counter(entry.status for entry in entries).items()))
    accepted_count = sum(entry.accepted for entry in entries)
    evidence = {
        "root_path": str(root),
        "recursive": recursive,
        "entries": [entry.to_dict() for entry in entries],
        "status_counts": status_counts,
    }
    return PDFPreflightBatchReport(
        root_path=str(root),
        recursive=recursive,
        total_count=len(entries),
        accepted_count=accepted_count,
        rejected_count=len(entries) - accepted_count,
        status_counts=status_counts,
        entries=tuple(entries),
        fingerprint=canonical_json_sha256(evidence),
    )


__all__ = ["PDFPreflightBatchReport", "preflight_pdf_batch"]
