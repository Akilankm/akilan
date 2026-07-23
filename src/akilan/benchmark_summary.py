"""Deterministic aggregate performance evidence for benchmark corpus reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .benchmark import CorpusReport


@dataclass(frozen=True, slots=True)
class CorpusPerformanceSummary:
    """Aggregate process-local performance evidence for one corpus run."""

    measured_case_count: int
    cache_hit_count: int
    cache_hit_ratio: float
    total_elapsed_seconds: float
    total_source_size_bytes: int
    total_output_size_bytes: int
    total_page_count: int
    pages_per_second: float
    source_mib_per_second: float
    peak_python_memory_bytes: int
    phase_seconds: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic machine-readable evidence."""

        return {
            "measured_case_count": self.measured_case_count,
            "cache_hit_count": self.cache_hit_count,
            "cache_hit_ratio": self.cache_hit_ratio,
            "total_elapsed_seconds": self.total_elapsed_seconds,
            "total_source_size_bytes": self.total_source_size_bytes,
            "total_output_size_bytes": self.total_output_size_bytes,
            "total_page_count": self.total_page_count,
            "pages_per_second": self.pages_per_second,
            "source_mib_per_second": self.source_mib_per_second,
            "peak_python_memory_bytes": self.peak_python_memory_bytes,
            "phase_seconds": dict(self.phase_seconds),
        }


def summarize_corpus_performance(report: CorpusReport) -> CorpusPerformanceSummary:
    """Aggregate per-case benchmark evidence without mutating the report.

    Failed cases contribute elapsed time, byte counts, memory, and phase timing
    when performance evidence exists. Page throughput counts only pages from
    successfully materialized artifacts. Peak memory is the maximum observed
    process-local peak rather than a misleading sum of independent peaks.
    """

    measured = [case for case in report.cases if case.performance is not None]
    elapsed = sum(case.elapsed_seconds for case in measured)
    source_size = sum(case.performance.source_size_bytes for case in measured if case.performance)
    output_size = sum(case.performance.output_size_bytes for case in measured if case.performance)
    page_count = sum(case.metrics.page_count for case in measured if case.metrics is not None)
    cache_hits = sum(bool(case.performance and case.performance.cache_hit) for case in measured)
    peak_memory = max(
        (case.performance.peak_python_memory_bytes for case in measured if case.performance),
        default=0,
    )

    phases: dict[str, float] = {}
    for case in measured:
        assert case.performance is not None
        for name, duration in case.performance.phase_seconds.items():
            phases[name] = phases.get(name, 0.0) + max(0.0, duration)

    safe_elapsed = max(elapsed, 1e-9)
    mib = 1024 * 1024
    measured_count = len(measured)
    return CorpusPerformanceSummary(
        measured_case_count=measured_count,
        cache_hit_count=cache_hits,
        cache_hit_ratio=round(cache_hits / measured_count, 6) if measured_count else 0.0,
        total_elapsed_seconds=round(max(0.0, elapsed), 6),
        total_source_size_bytes=source_size,
        total_output_size_bytes=output_size,
        total_page_count=page_count,
        pages_per_second=round(page_count / safe_elapsed, 6) if measured_count else 0.0,
        source_mib_per_second=round((source_size / mib) / safe_elapsed, 6) if measured_count else 0.0,
        peak_python_memory_bytes=peak_memory,
        phase_seconds={name: round(value, 6) for name, value in sorted(phases.items())},
    )
