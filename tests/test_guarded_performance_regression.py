from __future__ import annotations

import pytest

from akilan.benchmark_summary import CorpusPerformanceSummary
from akilan.guarded_performance_regression import compare_guarded_corpus_performance


def _summary(**overrides: float | int) -> CorpusPerformanceSummary:
    values: dict[str, object] = {
        "measured_case_count": 1,
        "cache_hit_count": 0,
        "cache_hit_ratio": 0.0,
        "total_elapsed_seconds": 5.0,
        "total_source_size_bytes": 1000,
        "total_output_size_bytes": 2000,
        "total_page_count": 10,
        "pages_per_second": 2.0,
        "source_mib_per_second": 0.00019,
        "peak_python_memory_bytes": 500,
        "phase_seconds": {"extract": 5.0},
    }
    values.update(overrides)
    return CorpusPerformanceSummary(**values)  # type: ignore[arg-type]


def test_matching_source_identity_and_performance_pass() -> None:
    fingerprint = "a" * 64
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint=fingerprint,
        baseline_source_fingerprint=fingerprint,
    )

    assert report.passed is True
    assert report.to_dict()["source_identity"]["matched"] is True
    assert report.violations == []


def test_source_mismatch_fails_with_exact_fingerprint_evidence() -> None:
    baseline = "a" * 64
    current = "b" * 64
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint=current,
        baseline_source_fingerprint=baseline,
    )

    assert report.passed is False
    assert report.to_dict()["violations"] == [
        {
            "metric": "source_guard_fingerprint",
            "expected": f"== {baseline}",
            "baseline": baseline,
            "current": current,
            "message": "current and baseline performance evidence describe different guarded source sets",
            "rule_id": "performance-source-identity-v1",
        }
    ]


def test_invalid_source_fingerprint_fails_closed() -> None:
    with pytest.raises(ValueError, match="64-character lowercase SHA-256"):
        compare_guarded_corpus_performance(
            _summary(),
            _summary(),
            current_source_fingerprint="invalid",
            baseline_source_fingerprint="a" * 64,
        )


def test_performance_and_source_violations_are_stably_ordered() -> None:
    report = compare_guarded_corpus_performance(
        _summary(pages_per_second=1.0),
        _summary(),
        current_source_fingerprint="b" * 64,
        baseline_source_fingerprint="a" * 64,
    )

    assert [violation.metric for violation in report.violations] == [
        "pages_per_second",
        "source_guard_fingerprint",
    ]
