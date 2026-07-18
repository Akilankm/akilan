"""Golden-subset expectations for corpus benchmark results.

The benchmark harness intentionally records stable aggregate evidence instead of
serializing brittle full-artifact snapshots. This module turns that evidence into
explicit, machine-readable acceptance decisions suitable for CI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .benchmark import ArtifactMetrics, CorpusCaseResult, CorpusReport
from .serialization import to_jsonable


@dataclass(frozen=True, slots=True)
class GoldenExpectation:
    """Stable acceptance criteria for one corpus case.

    Count minima protect evidence coverage while optional maxima detect accidental
    duplication. Fingerprints are opt-in because they are intentionally stricter
    than structural quality assertions.
    """

    min_page_count: int | None = None
    max_page_count: int | None = None
    min_text_block_count: int | None = None
    max_text_block_count: int | None = None
    min_table_count: int | None = None
    min_image_count: int | None = None
    min_drawing_count: int | None = None
    min_link_count: int | None = None
    min_annotation_count: int | None = None
    min_widget_count: int | None = None
    min_ordered_element_ratio: float | None = None
    required_semantic_roles: dict[str, int] = field(default_factory=dict)
    artifact_fingerprint: str | None = None

    def __post_init__(self) -> None:
        count_fields = (
            "min_page_count",
            "max_page_count",
            "min_text_block_count",
            "max_text_block_count",
            "min_table_count",
            "min_image_count",
            "min_drawing_count",
            "min_link_count",
            "min_annotation_count",
            "min_widget_count",
        )
        for name in count_fields:
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative")
        if (
            self.min_page_count is not None
            and self.max_page_count is not None
            and self.min_page_count > self.max_page_count
        ):
            raise ValueError("min_page_count cannot exceed max_page_count")
        if (
            self.min_text_block_count is not None
            and self.max_text_block_count is not None
            and self.min_text_block_count > self.max_text_block_count
        ):
            raise ValueError("min_text_block_count cannot exceed max_text_block_count")
        if self.min_ordered_element_ratio is not None and not 0.0 <= self.min_ordered_element_ratio <= 1.0:
            raise ValueError("min_ordered_element_ratio must be between 0 and 1")
        if any(count < 0 for count in self.required_semantic_roles.values()):
            raise ValueError("required semantic-role counts must be non-negative")
        if self.artifact_fingerprint is not None and len(self.artifact_fingerprint) != 64:
            raise ValueError("artifact_fingerprint must be a 64-character SHA-256 digest")


@dataclass(frozen=True, slots=True)
class BenchmarkViolation:
    """One actionable mismatch between expected and observed benchmark evidence."""

    source: str
    metric: str
    expectation: str
    actual: Any
    message: str


@dataclass(frozen=True, slots=True)
class BenchmarkAssessment:
    """Aggregate acceptance result for a corpus report."""

    evaluated_cases: int
    violations: list[BenchmarkViolation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "evaluated_cases": self.evaluated_cases,
                "passed": self.passed,
                "violation_count": len(self.violations),
            },
            "violations": to_jsonable(self.violations),
        }


def _metric_violation(
    case: CorpusCaseResult,
    metric: str,
    expectation: str,
    actual: Any,
) -> BenchmarkViolation:
    return BenchmarkViolation(
        source=case.source,
        metric=metric,
        expectation=expectation,
        actual=actual,
        message=f"{metric} expected {expectation}; observed {actual!r}",
    )


def _evaluate_metrics(
    case: CorpusCaseResult,
    metrics: ArtifactMetrics,
    expected: GoldenExpectation,
) -> list[BenchmarkViolation]:
    violations: list[BenchmarkViolation] = []
    minimums = {
        "page_count": expected.min_page_count,
        "text_block_count": expected.min_text_block_count,
        "table_count": expected.min_table_count,
        "image_count": expected.min_image_count,
        "drawing_count": expected.min_drawing_count,
        "link_count": expected.min_link_count,
        "annotation_count": expected.min_annotation_count,
        "widget_count": expected.min_widget_count,
        "ordered_element_ratio": expected.min_ordered_element_ratio,
    }
    maximums = {
        "page_count": expected.max_page_count,
        "text_block_count": expected.max_text_block_count,
    }
    for metric, threshold in minimums.items():
        actual = getattr(metrics, metric)
        if threshold is not None and actual < threshold:
            violations.append(_metric_violation(case, metric, f">= {threshold}", actual))
    for metric, threshold in maximums.items():
        actual = getattr(metrics, metric)
        if threshold is not None and actual > threshold:
            violations.append(_metric_violation(case, metric, f"<= {threshold}", actual))

    for role, minimum in sorted(expected.required_semantic_roles.items()):
        actual = metrics.semantic_role_counts.get(role, 0)
        if actual < minimum:
            violations.append(
                _metric_violation(case, f"semantic_role_counts.{role}", f">= {minimum}", actual)
            )

    if (
        expected.artifact_fingerprint is not None
        and metrics.artifact_fingerprint != expected.artifact_fingerprint
    ):
        violations.append(
            _metric_violation(
                case,
                "artifact_fingerprint",
                f"== {expected.artifact_fingerprint}",
                metrics.artifact_fingerprint,
            )
        )
    return violations


def assess_corpus(
    report: CorpusReport,
    expectations: dict[str, GoldenExpectation],
) -> BenchmarkAssessment:
    """Evaluate report cases against expectations keyed by source filename.

    A missing expected case and an extraction failure are explicit violations.
    Unlisted report cases are retained in the report but do not affect acceptance.
    """

    cases_by_name: dict[str, list[CorpusCaseResult]] = {}
    for case in report.cases:
        cases_by_name.setdefault(Path(case.source).name, []).append(case)

    violations: list[BenchmarkViolation] = []
    for source_name, expected in sorted(expectations.items()):
        matches = cases_by_name.get(source_name, [])
        if not matches:
            violations.append(
                BenchmarkViolation(
                    source=source_name,
                    metric="case_presence",
                    expectation="present exactly once",
                    actual=0,
                    message="expected corpus case was not present in the benchmark report",
                )
            )
            continue
        if len(matches) > 1:
            violations.append(
                BenchmarkViolation(
                    source=source_name,
                    metric="case_presence",
                    expectation="present exactly once",
                    actual=len(matches),
                    message="source filename is ambiguous; expectation keys must identify one case",
                )
            )
            continue
        case = matches[0]
        if case.status != "passed" or case.metrics is None:
            violations.append(
                BenchmarkViolation(
                    source=case.source,
                    metric="extraction_status",
                    expectation="passed",
                    actual=case.status,
                    message=f"extraction failed: {case.error_type or 'unknown'}: {case.error_message or ''}".rstrip(),
                )
            )
            continue
        violations.extend(_evaluate_metrics(case, case.metrics, expected))

    return BenchmarkAssessment(evaluated_cases=len(expectations), violations=violations)


def load_expectations(path: str | Path) -> dict[str, GoldenExpectation]:
    """Load strict JSON expectations keyed by corpus PDF filename."""

    source = Path(path).expanduser().resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expectation document must be a JSON object")
    expectations: dict[str, GoldenExpectation] = {}
    for filename, raw in payload.items():
        if not isinstance(filename, str) or not filename.lower().endswith(".pdf"):
            raise ValueError("expectation keys must be PDF filenames")
        if not isinstance(raw, dict):
            raise ValueError(f"expectation for {filename!r} must be an object")
        expectations[filename] = GoldenExpectation(**raw)
    return expectations


def write_assessment(assessment: BenchmarkAssessment, destination: str | Path) -> Path:
    """Persist deterministic machine-readable acceptance evidence."""

    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(assessment.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
