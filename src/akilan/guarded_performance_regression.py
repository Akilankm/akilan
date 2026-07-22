"""Performance regression checks bound to exact guarded source identity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .benchmark_summary import CorpusPerformanceSummary
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
class GuardedPerformanceRegressionReport:
    """Performance comparison plus exact guarded-source identity evidence."""

    performance: PerformanceRegressionReport
    source_identity: PerformanceSourceIdentity

    @property
    def passed(self) -> bool:
        return self.performance.passed and self.source_identity.matched

    @property
    def violations(self) -> list[PerformanceRegressionViolation]:
        violations = list(self.performance.violations)
        if not self.source_identity.matched:
            violations.append(
                PerformanceRegressionViolation(
                    metric="source_guard_fingerprint",
                    expected=f"== {self.source_identity.baseline_fingerprint}",
                    baseline=0,
                    current=1,
                    message=(
                        "current and baseline performance evidence describe different guarded source sets"
                    ),
                    rule_id="performance-source-identity-v1",
                )
            )
        return sorted(violations, key=lambda item: (item.metric, item.rule_id))

    def to_dict(self) -> dict[str, Any]:
        payload = self.performance.to_dict()
        violations = self.violations
        return {
            **payload,
            "passed": self.passed,
            "source_identity": {
                **asdict(self.source_identity),
                "matched": self.source_identity.matched,
            },
            "violation_count": len(violations),
            "violations": [asdict(violation) for violation in violations],
        }


def compare_guarded_corpus_performance(
    current: CorpusPerformanceSummary,
    baseline: CorpusPerformanceSummary,
    *,
    current_source_fingerprint: str,
    baseline_source_fingerprint: str,
    thresholds: PerformanceRegressionThresholds | None = None,
) -> GuardedPerformanceRegressionReport:
    """Compare performance only when exact guarded corpus identities are supplied."""

    identity = PerformanceSourceIdentity(
        baseline_fingerprint=baseline_source_fingerprint,
        current_fingerprint=current_source_fingerprint,
    )
    performance = compare_corpus_performance(current, baseline, thresholds)
    return GuardedPerformanceRegressionReport(
        performance=performance,
        source_identity=identity,
    )
