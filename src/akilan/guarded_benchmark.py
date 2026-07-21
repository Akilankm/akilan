"""Fail-closed benchmark execution over an exact, preflighted PDF source set."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .benchmark import CorpusReport, run_corpus
from .benchmark_source_guard import BenchmarkSourceGuardReport, guard_benchmark_sources
from .config import ExtractionConfig


class BenchmarkSourceGuardError(ValueError):
    """Raised when benchmark execution is blocked by source readiness evidence."""

    def __init__(self, report: BenchmarkSourceGuardReport) -> None:
        self.report = report
        rejected = ", ".join(
            f"{entry.source_path}: {entry.status}" for entry in report.entries if not entry.accepted
        )
        detail = rejected or "no benchmark sources were supplied"
        super().__init__(f"benchmark source guard rejected execution: {detail}")


def run_guarded_corpus(
    pdf_paths: Iterable[str | Path],
    output_root: str | Path,
    *,
    config: ExtractionConfig | None = None,
    use_cache: bool = True,
) -> CorpusReport:
    """Preflight the exact source set, then run the benchmark only when all PDFs are ready.

    Source paths are materialized once so generators are safe to pass. The guard runs before
    ``run_corpus`` creates the output root, canonical artifacts, or cache markers. Rejected and
    empty source sets raise :class:`BenchmarkSourceGuardError` with deterministic evidence.

    This boundary intentionally does not accept encrypted-PDF passwords yet because the current
    benchmark runner cannot forward per-source credentials into extraction. Encrypted inputs are
    therefore rejected rather than preflighted successfully and then failed later.
    """

    sources = tuple(pdf_paths)
    guard_report = guard_benchmark_sources(sources)
    if not guard_report.accepted:
        raise BenchmarkSourceGuardError(guard_report)

    normalized_sources = tuple(Path(entry.source_path) for entry in guard_report.entries)
    return run_corpus(
        normalized_sources,
        output_root,
        config=config,
        use_cache=use_cache,
    )


__all__ = ["BenchmarkSourceGuardError", "run_guarded_corpus"]
