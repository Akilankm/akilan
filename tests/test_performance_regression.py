from __future__ import annotations

import pytest

from akilan.benchmark_summary import CorpusPerformanceSummary
from akilan.performance_regression import (
    PerformanceRegressionThresholds,
    compare_corpus_performance,
)


def _summary(**overrides: float | int) -> CorpusPerformanceSummary:
    values: dict[str, object] = {
        "measured_case_count": 2,
        "cache_hit_count": 0,
        "cache_hit_ratio": 0.0,
        "total_elapsed_seconds": 10.0,
        "total_source_size_bytes": 2_000,
        "total_output_size_bytes": 8_000,
        "total_page_count": 20,
        "pages_per_second": 2.0,
        "source_mib_per_second": 0.000191,
        "peak_python_memory_bytes": 1_000,
        "phase_seconds": {"extract": 8.0, "persist": 2.0},
    }
    values.update(overrides)
    return CorpusPerformanceSummary(**values)  # type: ignore[arg-type]


def test_equivalent_run_within_tolerances_passes() -> None:
    report = compare_corpus_performance(
        _summary(
            total_elapsed_seconds=11.0,
            total_output_size_bytes=9_000,
            pages_per_second=1.8,
            peak_python_memory_bytes=1_100,
        ),
        _summary(),
    )

    assert report.passed is True
    assert report.to_dict()["violations"] == []


def test_material_regressions_are_reported_in_stable_metric_order() -> None:
    report = compare_corpus_performance(
        _summary(
            total_elapsed_seconds=13.0,
            total_output_size_bytes=11_000,
            pages_per_second=1.5,
            peak_python_memory_bytes=1_400,
        ),
        _summary(),
    )

    assert report.passed is False
    assert [violation.metric for violation in report.violations] == [
        "pages_per_second",
        "peak_python_memory_bytes",
        "total_elapsed_seconds",
        "total_output_size_bytes",
    ]
    assert {violation.rule_id for violation in report.violations} == {
        "performance-elapsed-seconds-regression-v1",
        "performance-output-size-regression-v1",
        "performance-pages-per-second-regression-v1",
        "performance-peak-memory-regression-v1",
    }


def test_different_workloads_fail_closed_without_relative_comparisons() -> None:
    report = compare_corpus_performance(
        _summary(measured_case_count=3, total_source_size_bytes=2_100, total_page_count=21),
        _summary(),
    )

    assert report.passed is False
    assert [violation.metric for violation in report.violations] == [
        "measured_case_count",
        "total_page_count",
        "total_source_size_bytes",
    ]
    assert {violation.rule_id for violation in report.violations} == {
        "performance-workload-equivalence-v1"
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("min_pages_per_second_ratio", -0.1),
        ("min_pages_per_second_ratio", 1.1),
        ("max_elapsed_seconds_increase_ratio", float("inf")),
        ("max_output_size_increase_ratio", -0.1),
        ("max_peak_memory_increase_ratio", float("nan")),
    ],
)
def test_invalid_thresholds_are_rejected(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        PerformanceRegressionThresholds(**{field: value})
