"""Corpus-level audit reporting for persisted benchmark cache entries."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .benchmark_cache_validation import (
    BENCHMARK_CACHE_FILENAME,
    BenchmarkCacheViolation,
    validate_benchmark_cache_entry,
)
from .canonical_json import canonical_json_fingerprint


@dataclass(frozen=True, slots=True)
class BenchmarkCacheAuditEntry:
    """Validation outcome for one benchmark artifact directory."""

    artifact_dir: str
    violations: tuple[BenchmarkCacheViolation, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_dir": self.artifact_dir,
            "valid": self.valid,
            "violations": [item.to_dict() for item in self.violations],
        }


@dataclass(frozen=True, slots=True)
class BenchmarkCacheAuditReport:
    """Deterministic audit evidence for a benchmark cache root."""

    root: str
    entries: tuple[BenchmarkCacheAuditEntry, ...] = field(default_factory=tuple)

    @property
    def valid_entries(self) -> int:
        return sum(entry.valid for entry in self.entries)

    @property
    def invalid_entries(self) -> int:
        return len(self.entries) - self.valid_entries

    @property
    def passed(self) -> bool:
        return bool(self.entries) and self.invalid_entries == 0

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "root": self.root,
            "summary": {
                "total": len(self.entries),
                "valid": self.valid_entries,
                "invalid": self.invalid_entries,
                "passed": self.passed,
            },
            "entries": [entry.to_dict() for entry in self.entries],
        }
        return {
            **payload,
            "report_fingerprint": canonical_json_fingerprint(payload),
        }


def audit_benchmark_cache(root: str | Path) -> BenchmarkCacheAuditReport:
    """Audit every benchmark cache marker below ``root`` without mutation.

    Only directories containing ``.akilan-benchmark-cache.json`` are treated as
    cache entries. Entries are resolved and returned in stable relative-path order.
    An empty root produces a failed report rather than silently passing.
    """

    resolved_root = Path(root).expanduser().resolve()
    if not resolved_root.exists():
        return BenchmarkCacheAuditReport(root=str(resolved_root))
    if not resolved_root.is_dir():
        raise NotADirectoryError(resolved_root)

    directories = sorted(
        {marker.parent for marker in resolved_root.rglob(BENCHMARK_CACHE_FILENAME)},
        key=lambda path: path.relative_to(resolved_root).as_posix(),
    )
    entries = tuple(
        BenchmarkCacheAuditEntry(
            artifact_dir=directory.relative_to(resolved_root).as_posix() or ".",
            violations=tuple(validate_benchmark_cache_entry(directory)),
        )
        for directory in directories
    )
    return BenchmarkCacheAuditReport(root=str(resolved_root), entries=entries)


def write_benchmark_cache_audit_report(
    report: BenchmarkCacheAuditReport,
    destination: str | Path,
) -> Path:
    """Persist deterministic, machine-readable audit evidence."""

    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
