"""Fail-closed benchmark execution over an exact, preflighted PDF source set."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class GuardedCorpusExecution:
    """Auditable result containing exact-source readiness and benchmark evidence."""

    guard_report: BenchmarkSourceGuardReport
    corpus_report: CorpusReport


def run_guarded_corpus_with_report(
    pdf_paths: Iterable[str | Path],
    output_root: str | Path,
    *,
    config: ExtractionConfig | None = None,
    use_cache: bool = True,
) -> GuardedCorpusExecution:
    """Preflight an exact source set and return both guard and benchmark evidence.

    Source paths are materialized once so generators are safe to pass. The guard runs before
    ``run_corpus`` creates the output root, canonical artifacts, or cache markers. Rejected and
    empty source sets raise :class:`BenchmarkSourceGuardError` with deterministic evidence.

    The returned guard report records the normalized, deduplicated source set that was accepted
    immediately before benchmark execution. This provides an auditable handoff without changing
    the established :class:`CorpusReport` contract.

    This boundary intentionally does not accept encrypted-PDF passwords yet because the current
    benchmark runner cannot forward per-source credentials into extraction. Encrypted inputs are
    therefore rejected rather than preflighted successfully and then failed later.
    """

    sources = tuple(pdf_paths)
    guard_report = guard_benchmark_sources(sources)
    if not guard_report.accepted:
        raise BenchmarkSourceGuardError(guard_report)

    normalized_sources = tuple(Path(entry.source_path) for entry in guard_report.entries)
    corpus_report = run_corpus(
        normalized_sources,
        output_root,
        config=config,
        use_cache=use_cache,
    )
    return GuardedCorpusExecution(guard_report=guard_report, corpus_report=corpus_report)


def run_guarded_corpus(
    pdf_paths: Iterable[str | Path],
    output_root: str | Path,
    *,
    config: ExtractionConfig | None = None,
    use_cache: bool = True,
) -> CorpusReport:
    """Preflight the exact source set, then return the established corpus report.

    Use :func:`run_guarded_corpus_with_report` when the successful source-guard evidence must be
    retained alongside benchmark results.
    """

    return run_guarded_corpus_with_report(
        pdf_paths,
        output_root,
        config=config,
        use_cache=use_cache,
    ).corpus_report


__all__ = [
    "BenchmarkSourceGuardError",
    "GuardedCorpusExecution",
    "run_guarded_corpus",
    "run_guarded_corpus_with_report",
]
