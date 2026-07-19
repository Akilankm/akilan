"""Deterministic acceptance gates for AKILAN corpus benchmark reports."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
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
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be a finite value between 0.0 and 1.0")
        if not math.isfinite(self.min_pages_per_second) or self.min_pages_per_second < 0.0:
            raise ValueError("min_pages_per_second must be finite and non-negative")
        maximum_ratio = self.max_output_to_source_ratio
        if maximum_ratio is not None and (not math.isfinite(maximum_ratio) or maximum_ratio < 0.0):
            raise ValueError("max_output_to_source_ratio must be finite and non-negative when provided")


@dataclass(frozen=True, slots=True)
class BenchmarkViolation:
    """One stable, machine-readable benchmark acceptance failure."""

    source: str
    metric: str
    expected: str
    actual: float | int | str | None
    message: str
    rule_id: str = "benchmark-acceptance-v1"


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

    Violations are returned in a stable order: corpus-level failures first,
    followed by case-level failures sorted by source, metric, and rule identifier.
    Invalid non-finite metric values are rejected explicitly instead of being
    allowed to bypass numeric threshold comparisons.
    """

    effective = thresholds or BenchmarkThresholds()
    violations: list[BenchmarkViolation] = []
    total = len(report.cases)
    if total == 0:
        violations.append(
            BenchmarkViolation(
                source="$corpus",
                metric="case_count",
                expected=">= 1",
                actual=0,
                message="benchmark corpus contains no cases",
                rule_id="benchmark-corpus-nonempty-v1",
            )
        )

    success_rate = report.succeeded / total if total else 0.0
    if success_rate < effective.min_success_rate:
        violations.append(
            BenchmarkViolation(
                source="$corpus",
                metric="success_rate",
                expected=f">= {effective.min_success_rate:.6f}",
                actual=round(success_rate, 6),
                message=f"corpus success rate {success_rate:.6f} is below the required threshold",
                rule_id="benchmark-success-rate-v1",
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
                    rule_id="benchmark-case-status-v1",
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
                    rule_id="benchmark-artifact-metrics-present-v1",
                )
            )
        else:
            ordered_ratio = case.metrics.ordered_element_ratio
            if not math.isfinite(ordered_ratio):
                case_violations.append(
                    BenchmarkViolation(
                        source=case.source,
                        metric="ordered_element_ratio",
                        expected="finite numeric value",
                        actual=str(ordered_ratio),
                        message="ordered element coverage is non-finite",
                        rule_id="benchmark-metric-finite-v1",
                    )
                )
            elif ordered_ratio < effective.min_ordered_element_ratio:
                case_violations.append(
                    BenchmarkViolation(
                        source=case.source,
                        metric="ordered_element_ratio",
                        expected=f">= {effective.min_ordered_element_ratio:.6f}",
                        actual=ordered_ratio,
                        message="ordered element coverage is below the required threshold",
                        rule_id="benchmark-ordered-element-ratio-v1",
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
                    rule_id="benchmark-performance-metrics-present-v1",
                )
            )
            continue

        throughput = case.performance.pages_per_second
        if not math.isfinite(throughput):
            case_violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="pages_per_second",
                    expected="finite numeric value",
                    actual=str(throughput),
                    message="page throughput is non-finite",
                    rule_id="benchmark-metric-finite-v1",
                )
            )
        elif throughput < effective.min_pages_per_second:
            case_violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="pages_per_second",
                    expected=f">= {effective.min_pages_per_second:.6f}",
                    actual=throughput,
                    message="page throughput is below the required threshold",
                    rule_id="benchmark-pages-per-second-v1",
                )
            )

        expansion_ratio = case.performance.output_to_source_ratio
        if not math.isfinite(expansion_ratio):
            case_violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="output_to_source_ratio",
                    expected="finite numeric value",
                    actual=str(expansion_ratio),
                    message="artifact expansion ratio is non-finite",
                    rule_id="benchmark-metric-finite-v1",
                )
            )
        else:
            maximum_ratio = effective.max_output_to_source_ratio
            if maximum_ratio is not None and expansion_ratio > maximum_ratio:
                case_violations.append(
                    BenchmarkViolation(
                        source=case.source,
                        metric="output_to_source_ratio",
                        expected=f"<= {maximum_ratio:.6f}",
                        actual=expansion_ratio,
                        message="artifact expansion ratio exceeds the allowed threshold",
                        rule_id="benchmark-output-expansion-ratio-v1",
                    )
                )

    violations.extend(sorted(case_violations, key=lambda item: (item.source, item.metric, item.rule_id)))
    return BenchmarkAcceptanceReport(thresholds=effective, violations=violations)


def write_benchmark_acceptance_report(
    report: BenchmarkAcceptanceReport,
    destination: str | Path,
) -> Path:
    """Persist stable acceptance evidence for CI and return the resolved path."""

    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
