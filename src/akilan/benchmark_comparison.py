"""Deterministic comparison of persisted AKILAN benchmark reports."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class BenchmarkRegressionThresholds:
    """Allowed relative performance regressions between two benchmark runs."""

    max_elapsed_increase_ratio: float = 0.0
    max_memory_increase_ratio: float = 0.0
    max_throughput_decrease_ratio: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "max_elapsed_increase_ratio",
            "max_memory_increase_ratio",
            "max_throughput_decrease_ratio",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a finite non-negative number")
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be a finite non-negative number")


@dataclass(frozen=True, slots=True)
class BenchmarkRegression:
    """One stable, machine-readable regression finding."""

    source: str
    metric: str
    baseline: float | int | str | None
    candidate: float | int | str | None
    allowed_ratio: float | None
    actual_ratio: float | None
    message: str
    rule_id: str


@dataclass(frozen=True, slots=True)
class BenchmarkComparisonReport:
    """Comparison outcome for a baseline and candidate benchmark report."""

    thresholds: BenchmarkRegressionThresholds
    baseline_case_count: int
    candidate_case_count: int
    compared_case_count: int
    regressions: list[BenchmarkRegression] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.regressions

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "thresholds": asdict(self.thresholds),
            "baseline_case_count": self.baseline_case_count,
            "candidate_case_count": self.candidate_case_count,
            "compared_case_count": self.compared_case_count,
            "regression_count": len(self.regressions),
            "regressions": [asdict(item) for item in self.regressions],
        }


def _load_report(value: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        payload = value
    else:
        path = Path(value).expanduser().resolve()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot load benchmark report {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("benchmark report must contain a cases array")
    return payload


def _passed_cases(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(payload["cases"]):
        if not isinstance(item, dict):
            raise ValueError(f"benchmark case at index {index} must be an object")
        source = item.get("source")
        if not isinstance(source, str) or not source:
            raise ValueError(f"benchmark case at index {index} has an invalid source")
        if source in cases:
            raise ValueError(f"benchmark report contains duplicate source {source!r}")
        if item.get("status") == "passed":
            cases[source] = item
    return cases


def _finite_number(value: Any, *, source: str, metric: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{source}: {metric} must be a finite non-negative number")
    return float(value)


def _increase_ratio(baseline: float, candidate: float) -> float:
    if baseline == 0.0:
        return 0.0 if candidate == 0.0 else math.inf
    return (candidate - baseline) / baseline


def _decrease_ratio(baseline: float, candidate: float) -> float:
    if baseline == 0.0:
        return 0.0
    return (baseline - candidate) / baseline


def compare_benchmark_reports(
    baseline: str | Path | dict[str, Any],
    candidate: str | Path | dict[str, Any],
    thresholds: BenchmarkRegressionThresholds | None = None,
) -> BenchmarkComparisonReport:
    """Compare common successful cases and report deterministic regressions."""

    effective = thresholds or BenchmarkRegressionThresholds()
    baseline_cases = _passed_cases(_load_report(baseline))
    candidate_cases = _passed_cases(_load_report(candidate))
    common_sources = sorted(baseline_cases.keys() & candidate_cases.keys())
    regressions: list[BenchmarkRegression] = []

    for source in sorted(baseline_cases.keys() - candidate_cases.keys()):
        regressions.append(
            BenchmarkRegression(
                source=source,
                metric="case_presence",
                baseline="passed",
                candidate="missing_or_failed",
                allowed_ratio=None,
                actual_ratio=None,
                message="baseline successful case is missing or failed in the candidate report",
                rule_id="benchmark-case-regression-v1",
            )
        )

    for source in common_sources:
        baseline_case = baseline_cases[source]
        candidate_case = candidate_cases[source]
        baseline_elapsed = _finite_number(baseline_case.get("elapsed_seconds"), source=source, metric="elapsed_seconds")
        candidate_elapsed = _finite_number(candidate_case.get("elapsed_seconds"), source=source, metric="elapsed_seconds")
        elapsed_ratio = _increase_ratio(baseline_elapsed, candidate_elapsed)
        if elapsed_ratio > effective.max_elapsed_increase_ratio:
            regressions.append(
                BenchmarkRegression(
                    source=source,
                    metric="elapsed_seconds",
                    baseline=baseline_elapsed,
                    candidate=candidate_elapsed,
                    allowed_ratio=effective.max_elapsed_increase_ratio,
                    actual_ratio=elapsed_ratio,
                    message="candidate elapsed time regressed beyond the allowed ratio",
                    rule_id="benchmark-elapsed-regression-v1",
                )
            )

        baseline_performance = baseline_case.get("performance")
        candidate_performance = candidate_case.get("performance")
        if not isinstance(baseline_performance, dict) or not isinstance(candidate_performance, dict):
            raise ValueError(f"{source}: successful cases must contain performance evidence")

        baseline_memory = _finite_number(
            baseline_performance.get("peak_python_memory_bytes"),
            source=source,
            metric="peak_python_memory_bytes",
        )
        candidate_memory = _finite_number(
            candidate_performance.get("peak_python_memory_bytes"),
            source=source,
            metric="peak_python_memory_bytes",
        )
        memory_ratio = _increase_ratio(baseline_memory, candidate_memory)
        if memory_ratio > effective.max_memory_increase_ratio:
            regressions.append(
                BenchmarkRegression(
                    source=source,
                    metric="peak_python_memory_bytes",
                    baseline=baseline_memory,
                    candidate=candidate_memory,
                    allowed_ratio=effective.max_memory_increase_ratio,
                    actual_ratio=memory_ratio,
                    message="candidate peak Python memory regressed beyond the allowed ratio",
                    rule_id="benchmark-memory-regression-v1",
                )
            )

        baseline_throughput = _finite_number(
            baseline_performance.get("pages_per_second"),
            source=source,
            metric="pages_per_second",
        )
        candidate_throughput = _finite_number(
            candidate_performance.get("pages_per_second"),
            source=source,
            metric="pages_per_second",
        )
        throughput_ratio = _decrease_ratio(baseline_throughput, candidate_throughput)
        if throughput_ratio > effective.max_throughput_decrease_ratio:
            regressions.append(
                BenchmarkRegression(
                    source=source,
                    metric="pages_per_second",
                    baseline=baseline_throughput,
                    candidate=candidate_throughput,
                    allowed_ratio=effective.max_throughput_decrease_ratio,
                    actual_ratio=throughput_ratio,
                    message="candidate page throughput regressed beyond the allowed ratio",
                    rule_id="benchmark-throughput-regression-v1",
                )
            )

    return BenchmarkComparisonReport(
        thresholds=effective,
        baseline_case_count=len(baseline_cases),
        candidate_case_count=len(candidate_cases),
        compared_case_count=len(common_sources),
        regressions=sorted(regressions, key=lambda item: (item.source, item.metric, item.rule_id)),
    )


def write_benchmark_comparison_report(report: BenchmarkComparisonReport, destination: str | Path) -> Path:
    """Persist deterministic benchmark-comparison evidence."""

    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
