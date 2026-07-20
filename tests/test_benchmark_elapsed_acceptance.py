from __future__ import annotations

import math

import pytest

from akilan.benchmark import ArtifactMetrics, CorpusCaseResult, CorpusReport, PerformanceMetrics
from akilan.benchmark_acceptance import BenchmarkThresholds, evaluate_corpus


def _case(*, elapsed_seconds: float) -> CorpusCaseResult:
    return CorpusCaseResult(
        source="elapsed.pdf",
        output_dir="artifacts/elapsed",
        status="passed",
        elapsed_seconds=elapsed_seconds,
        metrics=ArtifactMetrics(
            source_sha256="a" * 64,
            page_count=1,
            text_block_count=1,
            table_count=0,
            image_count=0,
            drawing_count=0,
            link_count=0,
            annotation_count=0,
            widget_count=0,
            reading_order_item_count=1,
            ordered_element_ratio=1.0,
            semantic_role_counts={"body": 1},
            artifact_fingerprint="b" * 64,
        ),
        performance=PerformanceMetrics(
            source_size_bytes=100,
            output_size_bytes=200,
            peak_python_memory_bytes=4096,
            pages_per_second=10.0,
            source_mib_per_second=1.0,
            output_to_source_ratio=2.0,
        ),
    )


def test_elapsed_time_threshold_passes_at_boundary() -> None:
    result = evaluate_corpus(
        CorpusReport(cases=[_case(elapsed_seconds=2.5)]),
        BenchmarkThresholds(max_elapsed_seconds=2.5),
    )

    assert result.passed is True
    assert result.to_dict()["thresholds"]["max_elapsed_seconds"] == 2.5


def test_elapsed_time_threshold_reports_stable_violation() -> None:
    result = evaluate_corpus(
        CorpusReport(cases=[_case(elapsed_seconds=2.500001)]),
        BenchmarkThresholds(max_elapsed_seconds=2.5),
    )

    assert result.passed is False
    assert [(item.metric, item.rule_id, item.expected, item.actual) for item in result.violations] == [
        ("elapsed_seconds", "benchmark-elapsed-time-v1", "<= 2.500000", 2.500001)
    ]


@pytest.mark.parametrize("value", [-1.0, math.inf, math.nan, True, "1.0"])
def test_elapsed_time_threshold_rejects_invalid_configuration(value: object) -> None:
    with pytest.raises(ValueError, match="max_elapsed_seconds"):
        BenchmarkThresholds(max_elapsed_seconds=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [-1.0, math.inf, math.nan, True])
def test_elapsed_time_evidence_rejects_invalid_values(value: object) -> None:
    result = evaluate_corpus(CorpusReport(cases=[_case(elapsed_seconds=value)]))  # type: ignore[arg-type]

    assert result.passed is False
    violation = result.violations[0]
    assert violation.metric == "elapsed_seconds"
    assert violation.rule_id == "benchmark-elapsed-time-evidence-valid-v1"
