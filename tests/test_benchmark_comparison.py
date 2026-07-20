from __future__ import annotations

import math

import pytest

from akilan.benchmark_comparison import (
    BenchmarkRegressionThresholds,
    compare_benchmark_reports,
)


def _report(
    *,
    elapsed: float = 1.0,
    memory: int = 100,
    throughput: float = 10.0,
    status: str = "passed",
) -> dict[str, object]:
    return {
        "summary": {"total": 1, "succeeded": int(status == "passed"), "failed": int(status != "passed")},
        "cases": [
            {
                "source": "sample.pdf",
                "output_dir": "artifacts/sample",
                "status": status,
                "elapsed_seconds": elapsed,
                "metrics": {},
                "performance": {
                    "peak_python_memory_bytes": memory,
                    "pages_per_second": throughput,
                },
            }
        ],
    }


def test_comparison_passes_within_configured_regression_budgets() -> None:
    result = compare_benchmark_reports(
        _report(),
        _report(elapsed=1.05, memory=105, throughput=9.5),
        BenchmarkRegressionThresholds(
            max_elapsed_increase_ratio=0.051,
            max_memory_increase_ratio=0.051,
            max_throughput_decrease_ratio=0.051,
        ),
    )

    assert result.passed is True
    assert result.compared_case_count == 1
    assert result.regressions == []


def test_comparison_reports_stable_metric_regressions() -> None:
    result = compare_benchmark_reports(
        _report(),
        _report(elapsed=1.2, memory=130, throughput=8.0),
        BenchmarkRegressionThresholds(
            max_elapsed_increase_ratio=0.1,
            max_memory_increase_ratio=0.1,
            max_throughput_decrease_ratio=0.1,
        ),
    )

    assert result.passed is False
    assert [(item.metric, item.rule_id) for item in result.regressions] == [
        ("elapsed_seconds", "benchmark-elapsed-regression-v1"),
        ("pages_per_second", "benchmark-throughput-regression-v1"),
        ("peak_python_memory_bytes", "benchmark-memory-regression-v1"),
    ]


def test_comparison_fails_when_baseline_success_disappears() -> None:
    result = compare_benchmark_reports(_report(), _report(status="failed"))

    assert result.passed is False
    assert result.compared_case_count == 0
    assert result.regressions[0].rule_id == "benchmark-case-regression-v1"


@pytest.mark.parametrize("value", [-1.0, math.inf, math.nan, True, "0.1"])
def test_thresholds_reject_invalid_values(value: object) -> None:
    with pytest.raises(ValueError, match="finite non-negative number"):
        BenchmarkRegressionThresholds(max_elapsed_increase_ratio=value)  # type: ignore[arg-type]


def test_comparison_rejects_duplicate_sources() -> None:
    report = _report()
    report["cases"] = [*report["cases"], *report["cases"]]  # type: ignore[index]

    with pytest.raises(ValueError, match="duplicate source"):
        compare_benchmark_reports(report, _report())
