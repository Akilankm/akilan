from __future__ import annotations

import json
from pathlib import Path

import pytest

from akilan.benchmark import ArtifactMetrics, CorpusCaseResult, CorpusReport, PerformanceMetrics
from akilan.benchmark_acceptance import (
    BenchmarkThresholds,
    evaluate_corpus,
    write_benchmark_acceptance_report,
)


def _metrics(*, ordered_element_ratio: float = 1.0) -> ArtifactMetrics:
    return ArtifactMetrics(
        source_sha256="a" * 64,
        page_count=2,
        text_block_count=4,
        table_count=0,
        image_count=0,
        drawing_count=0,
        link_count=0,
        annotation_count=0,
        widget_count=0,
        reading_order_item_count=4,
        ordered_element_ratio=ordered_element_ratio,
        semantic_role_counts={"body": 4},
        artifact_fingerprint="b" * 64,
    )


def _performance(
    *,
    pages_per_second: float = 10.0,
    output_to_source_ratio: float = 2.0,
) -> PerformanceMetrics:
    return PerformanceMetrics(
        source_size_bytes=100,
        output_size_bytes=200,
        peak_python_memory_bytes=1024,
        pages_per_second=pages_per_second,
        source_mib_per_second=1.0,
        output_to_source_ratio=output_to_source_ratio,
    )


def _passed_case(source: str, **overrides: object) -> CorpusCaseResult:
    values: dict[str, object] = {
        "source": source,
        "output_dir": f"artifacts/{source}",
        "status": "passed",
        "elapsed_seconds": 0.2,
        "metrics": _metrics(),
        "performance": _performance(),
    }
    values.update(overrides)
    return CorpusCaseResult(**values)  # type: ignore[arg-type]


def test_evaluate_corpus_passes_when_all_thresholds_are_met() -> None:
    report = CorpusReport(cases=[_passed_case("a.pdf"), _passed_case("b.pdf")])

    result = evaluate_corpus(
        report,
        BenchmarkThresholds(
            min_success_rate=1.0,
            min_ordered_element_ratio=0.99,
            min_pages_per_second=5.0,
            max_output_to_source_ratio=3.0,
        ),
    )

    assert result.passed is True
    assert result.to_dict()["violation_count"] == 0


def test_evaluate_corpus_reports_corpus_and_case_failures() -> None:
    report = CorpusReport(
        cases=[
            _passed_case("good.pdf"),
            CorpusCaseResult(
                source="broken.pdf",
                output_dir="artifacts/broken",
                status="failed",
                elapsed_seconds=0.1,
                error_type="RuntimeError",
                error_message="cannot parse source",
            ),
        ]
    )

    result = evaluate_corpus(report, BenchmarkThresholds(min_success_rate=1.0))

    assert result.passed is False
    assert [(item.source, item.metric) for item in result.violations] == [
        ("$corpus", "success_rate"),
        ("broken.pdf", "status"),
    ]
    assert result.violations[1].message == "cannot parse source"
    assert result.violations[1].rule_id == "benchmark-case-status-v1"


def test_evaluate_corpus_reports_quality_and_performance_thresholds() -> None:
    report = CorpusReport(
        cases=[
            _passed_case(
                "weak.pdf",
                metrics=_metrics(ordered_element_ratio=0.75),
                performance=_performance(pages_per_second=1.5, output_to_source_ratio=8.0),
            )
        ]
    )

    result = evaluate_corpus(
        report,
        BenchmarkThresholds(
            min_ordered_element_ratio=0.9,
            min_pages_per_second=2.0,
            max_output_to_source_ratio=4.0,
        ),
    )

    assert [item.metric for item in result.violations] == [
        "ordered_element_ratio",
        "output_to_source_ratio",
        "pages_per_second",
    ]


def test_evaluate_corpus_rejects_passed_cases_without_evidence() -> None:
    result = evaluate_corpus(
        CorpusReport(cases=[_passed_case("missing.pdf", metrics=None, performance=None)])
    )

    assert [(item.source, item.metric) for item in result.violations] == [
        ("missing.pdf", "metrics"),
        ("missing.pdf", "performance"),
    ]


def test_evaluate_corpus_rejects_empty_corpus_explicitly() -> None:
    result = evaluate_corpus(CorpusReport())

    assert result.passed is False
    assert [(item.metric, item.rule_id) for item in result.violations] == [
        ("case_count", "benchmark-corpus-nonempty-v1"),
        ("success_rate", "benchmark-success-rate-v1"),
    ]


def test_evaluate_corpus_rejects_non_finite_metric_values() -> None:
    report = CorpusReport(
        cases=[
            _passed_case(
                "invalid.pdf",
                metrics=_metrics(ordered_element_ratio=float("nan")),
                performance=_performance(
                    pages_per_second=float("inf"),
                    output_to_source_ratio=float("nan"),
                ),
            )
        ]
    )

    result = evaluate_corpus(report)

    assert result.passed is False
    assert [(item.metric, item.rule_id) for item in result.violations] == [
        ("ordered_element_ratio", "benchmark-metric-finite-v1"),
        ("output_to_source_ratio", "benchmark-metric-finite-v1"),
        ("pages_per_second", "benchmark-metric-finite-v1"),
    ]
    assert [item.actual for item in result.violations] == ["nan", "nan", "inf"]


def test_acceptance_report_is_stable_json(tmp_path: Path) -> None:
    result = evaluate_corpus(CorpusReport(cases=[_passed_case("stable.pdf")]))

    path = write_benchmark_acceptance_report(result, tmp_path / "reports" / "acceptance.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload == result.to_dict()
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_thresholds_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="min_success_rate"):
        BenchmarkThresholds(min_success_rate=1.1)
    with pytest.raises(ValueError, match="min_ordered_element_ratio"):
        BenchmarkThresholds(min_ordered_element_ratio=-0.1)
    with pytest.raises(ValueError, match="min_pages_per_second"):
        BenchmarkThresholds(min_pages_per_second=-1.0)
    with pytest.raises(ValueError, match="max_output_to_source_ratio"):
        BenchmarkThresholds(max_output_to_source_ratio=-1.0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("min_success_rate", float("nan")),
        ("min_ordered_element_ratio", float("inf")),
        ("min_pages_per_second", float("nan")),
        ("max_output_to_source_ratio", float("inf")),
    ],
)
def test_thresholds_reject_non_finite_values(field: str, value: float) -> None:
    with pytest.raises(ValueError, match=field):
        BenchmarkThresholds(**{field: value})
