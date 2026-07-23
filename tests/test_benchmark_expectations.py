from __future__ import annotations

import json
from pathlib import Path

import pytest

from akilan.benchmark import ArtifactMetrics, CorpusCaseResult, CorpusReport
from akilan.benchmark_expectations import (
    GoldenExpectation,
    assess_corpus,
    load_expectations,
    write_assessment,
)


def _metrics(**overrides: object) -> ArtifactMetrics:
    values: dict[str, object] = {
        "source_sha256": "a" * 64,
        "page_count": 2,
        "text_block_count": 8,
        "table_count": 1,
        "image_count": 1,
        "drawing_count": 0,
        "link_count": 0,
        "annotation_count": 0,
        "widget_count": 0,
        "reading_order_item_count": 10,
        "ordered_element_ratio": 1.0,
        "semantic_role_counts": {"heading_1": 1, "paragraph": 7},
        "artifact_fingerprint": "b" * 64,
    }
    values.update(overrides)
    return ArtifactMetrics(**values)  # type: ignore[arg-type]


def _passed_case(name: str = "complex.pdf", **metric_overrides: object) -> CorpusCaseResult:
    return CorpusCaseResult(
        source=f"/corpus/{name}",
        output_dir=f"/artifacts/{name}",
        status="passed",
        elapsed_seconds=0.1,
        metrics=_metrics(**metric_overrides),
    )


def test_assess_corpus_passes_structural_golden_subset() -> None:
    report = CorpusReport(cases=[_passed_case()])
    expectation = GoldenExpectation(
        min_page_count=2,
        max_page_count=2,
        min_text_block_count=5,
        min_table_count=1,
        min_image_count=1,
        min_ordered_element_ratio=0.95,
        required_semantic_roles={"heading_1": 1, "paragraph": 5},
    )

    assessment = assess_corpus(report, {"complex.pdf": expectation})

    assert assessment.passed is True
    assert assessment.evaluated_cases == 1
    assert assessment.violations == []


def test_assess_corpus_reports_actionable_metric_mismatches() -> None:
    report = CorpusReport(
        cases=[
            _passed_case(
                page_count=1,
                text_block_count=3,
                table_count=0,
                ordered_element_ratio=0.5,
                semantic_role_counts={"paragraph": 3},
            )
        ]
    )
    expectation = GoldenExpectation(
        min_page_count=2,
        min_text_block_count=5,
        min_table_count=1,
        min_ordered_element_ratio=0.9,
        required_semantic_roles={"heading_1": 1},
    )

    assessment = assess_corpus(report, {"complex.pdf": expectation})

    assert assessment.passed is False
    assert [violation.metric for violation in assessment.violations] == [
        "page_count",
        "text_block_count",
        "table_count",
        "ordered_element_ratio",
        "semantic_role_counts.heading_1",
    ]
    assert all(violation.source.endswith("complex.pdf") for violation in assessment.violations)


def test_assess_corpus_reports_missing_failed_and_ambiguous_cases() -> None:
    report = CorpusReport(
        cases=[
            CorpusCaseResult(
                source="/corpus/broken.pdf",
                output_dir="/artifacts/broken",
                status="failed",
                elapsed_seconds=0.1,
                error_type="FileDataError",
                error_message="cannot open broken document",
            ),
            _passed_case("duplicate.pdf"),
            _passed_case("duplicate.pdf"),
        ]
    )
    expectations = {
        "missing.pdf": GoldenExpectation(min_page_count=1),
        "broken.pdf": GoldenExpectation(min_page_count=1),
        "duplicate.pdf": GoldenExpectation(min_page_count=1),
    }

    assessment = assess_corpus(report, expectations)

    assert [violation.metric for violation in assessment.violations] == [
        "extraction_status",
        "case_presence",
        "case_presence",
    ]
    assert "FileDataError" in assessment.violations[0].message


def test_load_expectations_and_write_assessment_are_deterministic(tmp_path: Path) -> None:
    expectation_path = tmp_path / "expectations.json"
    expectation_path.write_text(
        json.dumps(
            {
                "complex.pdf": {
                    "min_page_count": 2,
                    "min_ordered_element_ratio": 0.9,
                    "required_semantic_roles": {"heading_1": 1},
                }
            }
        ),
        encoding="utf-8",
    )

    expectations = load_expectations(expectation_path)
    assessment = assess_corpus(CorpusReport(cases=[_passed_case()]), expectations)
    output = write_assessment(assessment, tmp_path / "reports" / "assessment.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload == {
        "summary": {"evaluated_cases": 1, "passed": True, "violation_count": 0},
        "violations": [],
    }


def test_expectation_validation_rejects_invalid_contracts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        GoldenExpectation(min_ordered_element_ratio=1.1)
    with pytest.raises(ValueError, match="cannot exceed"):
        GoldenExpectation(min_page_count=3, max_page_count=2)

    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({"not-a-pdf": {"min_page_count": 1}}), encoding="utf-8")
    with pytest.raises(ValueError, match="PDF filenames"):
        load_expectations(invalid)
