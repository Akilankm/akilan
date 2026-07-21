"""Fail-closed readiness guard for an exact benchmark source set."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .canonical_json import canonical_json_fingerprint
from .pdf_preflight import PDFPreflightReport, preflight_pdf


@dataclass(frozen=True, slots=True)
class BenchmarkSourceGuardReport:
    """Deterministic evidence that selected benchmark sources are extraction-ready."""

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


def guard_benchmark_sources(
    sources: Iterable[str | Path],
    *,
    passwords: dict[str, str] | None = None,
) -> BenchmarkSourceGuardReport:
    """Preflight an exact source set before benchmark artifacts or cache entries are created.

    Sources are normalized, deduplicated, and ordered by absolute path. Password lookup keys
    may be either the original supplied path string or the normalized absolute path. Password
    values are passed only to ``preflight_pdf`` and are never persisted in report evidence.
    """

    password_map = passwords or {}
    normalized_by_original: dict[str, Path] = {}
    for source in sources:
        original = str(source)
        normalized_by_original[original] = Path(source).expanduser().resolve()

    normalized_sources = tuple(sorted(set(normalized_by_original.values()), key=str))
    entries: list[PDFPreflightReport] = []
    for source in normalized_sources:
        password = password_map.get(str(source))
        if password is None:
            matching_original = next(
                (original for original, normalized in normalized_by_original.items() if normalized == source),
                None,
            )
            if matching_original is not None:
                password = password_map.get(matching_original)
        entries.append(preflight_pdf(source, password=password))

    status_counts = dict(sorted(Counter(entry.status for entry in entries).items()))
    accepted_count = sum(entry.accepted for entry in entries)
    evidence = {
        "entries": [entry.to_dict() for entry in entries],
        "status_counts": status_counts,
    }
    return BenchmarkSourceGuardReport(
        total_count=len(entries),
        accepted_count=accepted_count,
        rejected_count=len(entries) - accepted_count,
        status_counts=status_counts,
        entries=tuple(entries),
        fingerprint=canonical_json_fingerprint(evidence),
    )


__all__ = ["BenchmarkSourceGuardReport", "guard_benchmark_sources"]
