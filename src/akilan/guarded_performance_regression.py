"""Performance regression checks bound to guarded source and execution identity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .benchmark_summary import CorpusPerformanceSummary
from .performance_execution_identity import PerformanceExecutionIdentity
from .performance_regression import (
    PerformanceRegressionReport,
    PerformanceRegressionThresholds,
    PerformanceRegressionViolation,
    compare_corpus_performance,
)


@dataclass(frozen=True, slots=True)
class PerformanceSourceIdentity:
    """Validated source-set identity used for a performance comparison."""

    baseline_fingerprint: str
    current_fingerprint: str

    def __post_init__(self) -> None:
        for name in ("baseline_fingerprint", "current_fingerprint"):
            value = getattr(self, name)
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"{name} must be a 64-character lowercase SHA-256 fingerprint")

    @property
    def matched(self) -> bool:
        return self.baseline_fingerprint == self.current_fingerprint


@dataclass(frozen=True, slots=True)
class PerformanceExecutionIdentityComparison:
    """Validated execution-context identity used for a performance comparison."""

    baseline: PerformanceExecutionIdentity
    current: PerformanceExecutionIdentity

    @property
    def baseline_valid(self) -> bool:
        return self.baseline.valid

    @property
    def current_valid(self) -> bool:
        return self.current.valid

    @property
    def matched(self) -> bool:
        return (
            self.baseline_valid
            and self.current_valid
            and self.baseline.fingerprint == self.current.fingerprint
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_fingerprint": self.baseline.fingerprint,
            "current_fingerprint": self.current.fingerprint,
            "baseline_valid": self.baseline_valid,
            "current_valid": self.current_valid,
            "matched": self.matched,
        }


@dataclass(frozen=True, slots=True)
class GuardedPerformanceRegressionReport:
    """Performance comparison plus source and optional execution identity evidence."""

    performance: PerformanceRegressionReport
    source_identity: PerformanceSourceIdentity
    execution_identity: PerformanceExecutionIdentityComparison | None = None

    @property
    def passed(self) -> bool:
        execution_passed = self.execution_identity is None or self.execution_identity.matched
        return self.performance.passed and self.source_identity.matched and execution_passed

    @property
    def violations(self) -> list[PerformanceRegressionViolation]:
        violations = list(self.performance.violations)
        if not self.source_identity.matched:
            violations.append(
                PerformanceRegressionViolation(
                    metric="source_guard_fingerprint",
                    expected=f"== {self.source_identity.baseline_fingerprint}",
                    baseline=self.source_identity.baseline_fingerprint,
                    current=self.source_identity.current_fingerprint,
                    message=(
                        "current and baseline performance evidence describe different guarded source sets"
                    ),
                    rule_id="performance-source-identity-v1",
                )
            )
        if self.execution_identity is not None and not self.execution_identity.matched:
            violations.append(
                PerformanceRegressionViolation(
                    metric="execution_identity_fingerprint",
                    expected=f"== {self.execution_identity.baseline.fingerprint}",
                    baseline=self.execution_identity.baseline.fingerprint,
                    current=self.execution_identity.current.fingerprint,
                    message=(
                        "current and baseline performance evidence describe different or invalid execution contexts"
                    ),
                    rule_id="performance-execution-identity-v1",
                )
            )
        return sorted(violations, key=lambda item: (item.metric, item.rule_id))

    def to_dict(self) -> dict[str, Any]:
        violations = self.violations
        return {
            **self.performance.to_dict(),
            "passed": self.passed,
            "source_identity": {
                **asdict(self.source_identity),
                "matched": self.source_identity.matched,
            },
            "execution_identity": (
                None if self.execution_identity is None else self.execution_identity.to_dict()
            ),
            "violation_count": len(violations),
            "violations": [asdict(violation) for violation in violations],
        }


def compare_guarded_corpus_performance(
    current: CorpusPerformanceSummary,
    baseline: CorpusPerformanceSummary,
    *,
    current_source_fingerprint: str,
    baseline_source_fingerprint: str,
    current_execution_identity: PerformanceExecutionIdentity | None = None,
    baseline_execution_identity: PerformanceExecutionIdentity | None = None,
    thresholds: PerformanceRegressionThresholds | None = None,
) -> GuardedPerformanceRegressionReport:
    """Compare performance with exact guarded corpus and optional execution identity.

    Execution identity inputs are an all-or-nothing pair. Omitting both preserves
    the established source-only comparison contract. Supplying both additionally
    fails closed for invalid, tampered, or mismatched runtime/configuration evidence.
    """

    if (current_execution_identity is None) != (baseline_execution_identity is None):
        raise ValueError("baseline and current execution identities must be supplied together")

    source_identity = PerformanceSourceIdentity(
        baseline_fingerprint=baseline_source_fingerprint,
        current_fingerprint=current_source_fingerprint,
    )
    execution_identity = None
    if current_execution_identity is not None and baseline_execution_identity is not None:
        execution_identity = PerformanceExecutionIdentityComparison(
            baseline=baseline_execution_identity,
            current=current_execution_identity,
        )

    return GuardedPerformanceRegressionReport(
        performance=compare_corpus_performance(current, baseline, thresholds),
        source_identity=source_identity,
        execution_identity=execution_identity,
    )
