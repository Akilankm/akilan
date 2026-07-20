from __future__ import annotations

import pytest

from akilan.benchmark import ArtifactMetrics, CorpusCaseResult, CorpusReport, PerformanceMetrics
from akilan.benchmark_acceptance import BenchmarkThresholds, evaluate_corpus


def _case(*, peak_memory: int) -> CorpusCaseResult:
    return CorpusCaseResult(
        source="memory.pdf",
        output_dir="artifacts/memory",
        status="passed",
        elapsed_seconds=0.1,
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
            peak_python_memory_bytes=peak_memory,
            pages_per_second=10.0,
            source_mib_per_second=1.0,
            output_to_source_ratio=2.0,
        ),
    )


def test_peak_memory_threshold_passes_at_boundary() -> None:
    result = evaluate_corpus(
        CorpusReport(cases=[_case(peak_memory=4096)]),
        BenchmarkThresholds(max_peak_python_memory_bytes=4096),
    )

    assert result.passed is True
    assert result.to_dict()["thresholds"]["max_peak_python_memory_bytes"] == 4096


def test_peak_memory_threshold_reports_stable_violation() -> None:
    result = evaluate_corpus(
        CorpusReport(cases=[_case(peak_memory=4097)]),
        BenchmarkThresholds(max_peak_python_memory_bytes=4096),
    )

    assert result.passed is False
    assert [(item.metric, item.rule_id, item.expected, item.actual) for item in result.violations] == [
        ("peak_python_memory_bytes", "benchmark-peak-python-memory-v1", "<= 4096", 4097)
    ]


@pytest.mark.parametrize("value", [-1, 1.5, True])
def test_peak_memory_threshold_rejects_invalid_configuration(value: object) -> None:
    with pytest.raises(ValueError, match="max_peak_python_memory_bytes"):
        BenchmarkThresholds(max_peak_python_memory_bytes=value)  # type: ignore[arg-type]


def test_peak_memory_evidence_rejects_negative_values() -> None:
    result = evaluate_corpus(CorpusReport(cases=[_case(peak_memory=-1)]))

    assert result.passed is False
    violation = result.violations[0]
    assert violation.metric == "peak_python_memory_bytes"
    assert violation.rule_id == "benchmark-memory-evidence-valid-v1"
    assert violation.actual == -1
