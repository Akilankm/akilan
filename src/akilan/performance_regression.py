"""Deterministic regression checks for corpus performance summaries."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from .benchmark_summary import CorpusPerformanceSummary


@dataclass(frozen=True, slots=True)
class PerformanceRegressionThresholds:
    """Allowed relative regressions against an approved baseline."""

    min_pages_per_second_ratio: float = 0.8
    max_elapsed_seconds_increase_ratio: float = 0.25
    max_output_size_increase_ratio: float = 0.25
    max_peak_memory_increase_ratio: float = 0.25

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.min_pages_per_second_ratio)
            or not 0.0 <= self.min_pages_per_second_ratio <= 1.0
        ):
            raise ValueError("min_pages_per_second_ratio must be finite and between 0.0 and 1.0")
        for name in (
            "max_elapsed_seconds_increase_ratio",
            "max_output_size_increase_ratio",
            "max_peak_memory_increase_ratio",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class PerformanceRegressionViolation:
    """One stable, machine-readable performance regression."""

    metric: str
    expected: str
    baseline: float | int | str
    current: float | int | str
    message: str
    rule_id: str


@dataclass(frozen=True, slots=True)
class PerformanceRegressionReport:
    """Comparison result for current and baseline corpus performance."""

    thresholds: PerformanceRegressionThresholds
    violations: list[PerformanceRegressionViolation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "thresholds": asdict(self.thresholds),
            "violation_count": len(self.violations),
            "violations": [asdict(violation) for violation in self.violations],
        }


def _maximum_from_baseline(value: float | int, increase_ratio: float) -> float:
    return float(value) * (1.0 + increase_ratio)


def compare_corpus_performance(
    current: CorpusPerformanceSummary,
    baseline: CorpusPerformanceSummary,
    thresholds: PerformanceRegressionThresholds | None = None,
) -> PerformanceRegressionReport:
    """Compare equivalent corpus runs and fail closed on material regressions.

    Source bytes, page count, and measured-case count must match before relative
    performance comparisons are considered meaningful. Violations are emitted in
    stable metric order.
    """

    effective = thresholds or PerformanceRegressionThresholds()
    violations: list[PerformanceRegressionViolation] = []

    for metric in ("measured_case_count", "total_source_size_bytes", "total_page_count"):
        baseline_value = getattr(baseline, metric)
        current_value = getattr(current, metric)
        if current_value != baseline_value:
            violations.append(
                PerformanceRegressionViolation(
                    metric=metric,
                    expected=f"== {baseline_value}",
                    baseline=baseline_value,
                    current=current_value,
                    message="current and baseline performance evidence describe different workloads",
                    rule_id="performance-workload-equivalence-v1",
                )
            )

    if not violations:
        baseline_throughput = baseline.pages_per_second
        minimum_throughput = baseline_throughput * effective.min_pages_per_second_ratio
        if baseline_throughput > 0.0 and current.pages_per_second < minimum_throughput:
            violations.append(
                PerformanceRegressionViolation(
                    metric="pages_per_second",
                    expected=f">= {minimum_throughput:.6f}",
                    baseline=baseline_throughput,
                    current=current.pages_per_second,
                    message="page throughput regressed beyond the allowed ratio",
                    rule_id="performance-pages-per-second-regression-v1",
                )
            )

        comparisons = (
            (
                "total_elapsed_seconds",
                baseline.total_elapsed_seconds,
                current.total_elapsed_seconds,
                effective.max_elapsed_seconds_increase_ratio,
                "elapsed time increased beyond the allowed ratio",
                "performance-elapsed-seconds-regression-v1",
            ),
            (
                "total_output_size_bytes",
                baseline.total_output_size_bytes,
                current.total_output_size_bytes,
                effective.max_output_size_increase_ratio,
                "artifact output size increased beyond the allowed ratio",
                "performance-output-size-regression-v1",
            ),
            (
                "peak_python_memory_bytes",
                baseline.peak_python_memory_bytes,
                current.peak_python_memory_bytes,
                effective.max_peak_memory_increase_ratio,
                "peak Python memory increased beyond the allowed ratio",
                "performance-peak-memory-regression-v1",
            ),
        )
        for metric, baseline_value, current_value, increase_ratio, message, rule_id in comparisons:
            maximum = _maximum_from_baseline(baseline_value, increase_ratio)
            if current_value > maximum:
                violations.append(
                    PerformanceRegressionViolation(
                        metric=metric,
                        expected=f"<= {maximum:.6f}",
                        baseline=baseline_value,
                        current=current_value,
                        message=message,
                        rule_id=rule_id,
                    )
                )

    violations.sort(key=lambda item: (item.metric, item.rule_id))
    return PerformanceRegressionReport(thresholds=effective, violations=violations)
