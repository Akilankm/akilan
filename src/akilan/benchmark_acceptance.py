"""Deterministic acceptance gates for AKILAN corpus benchmark reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .benchmark import CorpusReport


@dataclass(frozen=True, slots=True)
class BenchmarkThresholds:
    """Minimum quality and performance requirements for a corpus run."""

    min_success_rate: float = 1.0
    min_ordered_element_ratio: float = 1.0
    min_pages_per_second: float = 0.0
    max_output_to_source_ratio: float | None = None

    def __post_init__(self) -> None:
        for name in ("min_success_rate", "min_ordered_element_ratio"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        if self.min_pages_per_second < 0.0:
            raise ValueError("min_pages_per_second must be non-negative")
        if self.max_output_to_source_ratio is not None and self.max_output_to_source_ratio < 0.0:
            raise ValueError("max_output_to_source_ratio must be non-negative when provided")


@dataclass(frozen=True, slots=True)
class BenchmarkViolation:
    """One stable, machine-readable benchmark acceptance failure."""

    source: str
    metric: str
    expected: str
    actual: float | int | str | None
    message: str


@dataclass(frozen=True, slots=True)
class BenchmarkAcceptanceReport:
    """Acceptance outcome for one corpus report and threshold set."""

    thresholds: BenchmarkThresholds
    violations: list[BenchmarkViolation] = field(default_factory=list)

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


def evaluate_corpus(
    report: CorpusReport,
    thresholds: BenchmarkThresholds | None = None,
) -> BenchmarkAcceptanceReport:
    """Evaluate a corpus report against deterministic acceptance thresholds.

    Violations are returned in a stable order: corpus-level success rate first,
    followed by case-level failures sorted by source and metric.
    """

    effective = thresholds or BenchmarkThresholds()
    violations: list[BenchmarkViolation] = []
    total = len(report.cases)
    success_rate = report.succeeded / total if total else 0.0
    if success_rate < effective.min_success_rate:
        violations.append(
            BenchmarkViolation(
                source="$corpus",
                metric="success_rate",
                expected=f">= {effective.min_success_rate:.6f}",
                actual=round(success_rate, 6),
                message=f"corpus success rate {success_rate:.6f} is below the required threshold",
            )
        )

    case_violations: list[BenchmarkViolation] = []
    for case in sorted(report.cases, key=lambda item: item.source):
        if case.status != "passed":
            case_violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="status",
                    expected="passed",
                    actual=case.status,
                    message=case.error_message or "benchmark case failed without an error message",
                )
            )
            continue

        if case.metrics is None:
            case_violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="metrics",
                    expected="present",
                    actual=None,
                    message="passed benchmark case has no artifact metrics",
                )
            )
        elif case.metrics.ordered_element_ratio < effective.min_ordered_element_ratio:
            case_violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="ordered_element_ratio",
                    expected=f">= {effective.min_ordered_element_ratio:.6f}",
                    actual=case.metrics.ordered_element_ratio,
                    message="ordered element coverage is below the required threshold",
                )
            )

        if case.performance is None:
            case_violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="performance",
                    expected="present",
                    actual=None,
                    message="passed benchmark case has no performance metrics",
                )
            )
            continue

        if case.performance.pages_per_second < effective.min_pages_per_second:
            case_violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="pages_per_second",
                    expected=f">= {effective.min_pages_per_second:.6f}",
                    actual=case.performance.pages_per_second,
                    message="page throughput is below the required threshold",
                )
            )
        maximum_ratio = effective.max_output_to_source_ratio
        if maximum_ratio is not None and case.performance.output_to_source_ratio > maximum_ratio:
            case_violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="output_to_source_ratio",
                    expected=f"<= {maximum_ratio:.6f}",
                    actual=case.performance.output_to_source_ratio,
                    message="artifact expansion ratio exceeds the allowed threshold",
                )
            )

    violations.extend(sorted(case_violations, key=lambda item: (item.source, item.metric)))
    return BenchmarkAcceptanceReport(thresholds=effective, violations=violations)
