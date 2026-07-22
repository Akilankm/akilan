from __future__ import annotations

from dataclasses import replace

import pytest
from akilan.benchmark_summary import CorpusPerformanceSummary
from akilan.canonical_json import canonical_json_fingerprint
from akilan.config import ExtractionConfig
from akilan.guarded_performance_regression import (
    compare_guarded_corpus_performance,
    verify_guarded_performance_regression_evidence,
)
from akilan.performance_execution_identity import build_performance_execution_identity


def _summary(**overrides: float | int) -> CorpusPerformanceSummary:
    values: dict[str, object] = {
        "measured_case_count": 1,
        "cache_hit_count": 0,
        "cache_hit_ratio": 0.0,
        "total_elapsed_seconds": 5.0,
        "total_source_size_bytes": 1000,
        "total_output_size_bytes": 2000,
        "total_page_count": 10,
        "pages_per_second": 2.0,
        "source_mib_per_second": 0.00019,
        "peak_python_memory_bytes": 500,
        "phase_seconds": {"extract": 5.0},
    }
    values.update(overrides)
    return CorpusPerformanceSummary(**values)  # type: ignore[arg-type]


def test_matching_source_identity_and_performance_pass() -> None:
    fingerprint = "a" * 64
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint=fingerprint,
        baseline_source_fingerprint=fingerprint,
    )

    assert report.passed is True
    assert report.to_dict()["source_identity"]["matched"] is True
    assert report.to_dict()["execution_identity"] is None
    assert report.violations == []


def test_source_mismatch_fails_with_exact_fingerprint_evidence() -> None:
    baseline = "a" * 64
    current = "b" * 64
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint=current,
        baseline_source_fingerprint=baseline,
    )

    assert report.passed is False
    assert report.to_dict()["violations"] == [
        {
            "metric": "source_guard_fingerprint",
            "expected": f"== {baseline}",
            "baseline": baseline,
            "current": current,
            "message": "current and baseline performance evidence describe different guarded source sets",
            "rule_id": "performance-source-identity-v1",
        }
    ]


def test_invalid_source_fingerprint_fails_closed() -> None:
    with pytest.raises(ValueError, match="64-character lowercase SHA-256"):
        compare_guarded_corpus_performance(
            _summary(),
            _summary(),
            current_source_fingerprint="invalid",
            baseline_source_fingerprint="a" * 64,
        )


def test_matching_execution_identity_passes() -> None:
    identity = build_performance_execution_identity(ExtractionConfig(render_pages=False))
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint="a" * 64,
        baseline_source_fingerprint="a" * 64,
        current_execution_identity=identity,
        baseline_execution_identity=identity,
    )

    evidence = report.to_dict()["execution_identity"]
    assert report.passed is True
    assert evidence == {
        "baseline_fingerprint": identity.fingerprint,
        "current_fingerprint": identity.fingerprint,
        "baseline_valid": True,
        "current_valid": True,
        "matched": True,
    }


def test_execution_identity_mismatch_fails_closed() -> None:
    baseline = build_performance_execution_identity(ExtractionConfig(render_pages=False))
    current = build_performance_execution_identity(ExtractionConfig(render_pages=True))
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint="a" * 64,
        baseline_source_fingerprint="a" * 64,
        current_execution_identity=current,
        baseline_execution_identity=baseline,
    )

    assert report.passed is False
    assert report.violations[0].rule_id == "performance-execution-identity-v1"
    assert report.to_dict()["execution_identity"]["matched"] is False


def test_tampered_execution_identity_fails_closed() -> None:
    baseline = build_performance_execution_identity()
    current = replace(baseline, fingerprint="f" * 64)
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint="a" * 64,
        baseline_source_fingerprint="a" * 64,
        current_execution_identity=current,
        baseline_execution_identity=baseline,
    )

    assert report.passed is False
    assert report.to_dict()["execution_identity"]["current_valid"] is False


def test_execution_identities_are_an_all_or_nothing_pair() -> None:
    identity = build_performance_execution_identity()
    with pytest.raises(ValueError, match="must be supplied together"):
        compare_guarded_corpus_performance(
            _summary(),
            _summary(),
            current_source_fingerprint="a" * 64,
            baseline_source_fingerprint="a" * 64,
            current_execution_identity=identity,
        )


def test_performance_and_identity_violations_are_stably_ordered() -> None:
    baseline_identity = build_performance_execution_identity(ExtractionConfig(render_pages=False))
    current_identity = build_performance_execution_identity(ExtractionConfig(render_pages=True))
    report = compare_guarded_corpus_performance(
        _summary(pages_per_second=1.0),
        _summary(),
        current_source_fingerprint="b" * 64,
        baseline_source_fingerprint="a" * 64,
        current_execution_identity=current_identity,
        baseline_execution_identity=baseline_identity,
    )

    assert [violation.metric for violation in report.violations] == [
        "execution_identity_fingerprint",
        "pages_per_second",
        "source_guard_fingerprint",
    ]


def test_evidence_fingerprint_protects_complete_decision_payload() -> None:
    identity = build_performance_execution_identity()
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint="a" * 64,
        baseline_source_fingerprint="a" * 64,
        current_execution_identity=identity,
        baseline_execution_identity=identity,
    )

    evidence = report.to_dict()
    fingerprint = evidence.pop("evidence_fingerprint")

    assert fingerprint == report.evidence_fingerprint
    assert fingerprint == canonical_json_fingerprint(evidence)
    assert len(fingerprint) == 64


def test_evidence_fingerprint_changes_when_decision_evidence_changes() -> None:
    baseline = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint="a" * 64,
        baseline_source_fingerprint="a" * 64,
    )
    regressed = compare_guarded_corpus_performance(
        _summary(pages_per_second=1.0),
        _summary(),
        current_source_fingerprint="a" * 64,
        baseline_source_fingerprint="a" * 64,
    )

    assert baseline.evidence_fingerprint != regressed.evidence_fingerprint


def test_persisted_evidence_verification_accepts_untampered_report() -> None:
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint="a" * 64,
        baseline_source_fingerprint="a" * 64,
    )

    verification = verify_guarded_performance_regression_evidence(report.to_dict())

    assert verification.valid is True
    assert verification.status == "valid"
    assert verification.expected_fingerprint == report.evidence_fingerprint
    assert verification.actual_fingerprint == report.evidence_fingerprint


def test_persisted_evidence_verification_rejects_tampered_payload() -> None:
    report = compare_guarded_corpus_performance(
        _summary(),
        _summary(),
        current_source_fingerprint="a" * 64,
        baseline_source_fingerprint="a" * 64,
    )
    evidence = report.to_dict()
    evidence["passed"] = False

    verification = verify_guarded_performance_regression_evidence(evidence)

    assert verification.valid is False
    assert verification.status == "fingerprint_mismatch"
    assert verification.expected_fingerprint != verification.actual_fingerprint


@pytest.mark.parametrize(
    "fingerprint",
    [None, "short", "A" * 64, 123],
)
def test_persisted_evidence_verification_rejects_invalid_fingerprint(
    fingerprint: object,
) -> None:
    evidence = {"passed": True, "evidence_fingerprint": fingerprint}

    verification = verify_guarded_performance_regression_evidence(evidence)

    assert verification.valid is False
    assert verification.status == "invalid_fingerprint"
    assert verification.expected_fingerprint is None
