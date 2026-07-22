from __future__ import annotations

import pytest

from akilan.canonical_json import canonical_json_fingerprint
from akilan.guarded_performance_evidence_policy import (
    verify_guarded_performance_evidence_policy,
    verify_guarded_performance_policy_evidence,
)


def _evidence(passed: object) -> dict[str, object]:
    payload: dict[str, object] = {"passed": passed, "violation_count": 0}
    return {**payload, "evidence_fingerprint": canonical_json_fingerprint(payload)}


def test_integrity_only_accepts_authentic_failed_decision() -> None:
    verification = verify_guarded_performance_evidence_policy(_evidence(False))

    assert verification.integrity.valid is True
    assert verification.decision_accepted is True
    assert verification.operational_status == "valid"
    assert verification.recorded_decision is False


def test_require_passed_accepts_only_authentic_true_decision() -> None:
    verification = verify_guarded_performance_evidence_policy(
        _evidence(True),
        require_passed=True,
    )

    assert verification.decision_accepted is True
    assert verification.operational_status == "accepted"
    assert verification.to_dict()["require_passed"] is True


def test_require_passed_rejects_authentic_failed_decision() -> None:
    verification = verify_guarded_performance_evidence_policy(
        _evidence(False),
        require_passed=True,
    )

    assert verification.integrity.valid is True
    assert verification.decision_accepted is False
    assert verification.operational_status == "recorded_decision_failed"


@pytest.mark.parametrize("recorded_decision", [None, "true", 1, 0])
def test_require_passed_rejects_missing_or_non_boolean_decision(
    recorded_decision: object,
) -> None:
    verification = verify_guarded_performance_evidence_policy(
        _evidence(recorded_decision),
        require_passed=True,
    )

    assert verification.integrity.valid is True
    assert verification.recorded_decision is None
    assert verification.decision_accepted is False
    assert verification.operational_status == "recorded_decision_missing"


def test_tampered_evidence_is_rejected_before_decision_policy() -> None:
    evidence = _evidence(True)
    evidence["passed"] = False

    verification = verify_guarded_performance_evidence_policy(
        evidence,
        require_passed=True,
    )

    assert verification.integrity.valid is False
    assert verification.decision_accepted is False
    assert verification.operational_status == "fingerprint_mismatch"


def test_policy_decision_evidence_has_recomputable_fingerprint() -> None:
    verification = verify_guarded_performance_evidence_policy(
        _evidence(True),
        require_passed=True,
    )
    payload = verification.to_dict()
    fingerprint = payload.pop("policy_evidence_fingerprint")

    assert fingerprint == verification.policy_evidence_fingerprint
    assert fingerprint == canonical_json_fingerprint(payload)


def test_policy_evidence_verifier_accepts_untampered_payload() -> None:
    payload = verify_guarded_performance_evidence_policy(
        _evidence(True),
        require_passed=True,
    ).to_dict()

    result = verify_guarded_performance_policy_evidence(payload)

    assert result.valid is True
    assert result.status == "valid"
    assert result.expected_fingerprint == result.actual_fingerprint


def test_policy_evidence_verifier_rejects_changed_policy_decision() -> None:
    payload = verify_guarded_performance_evidence_policy(
        _evidence(True),
        require_passed=True,
    ).to_dict()
    payload["decision_accepted"] = False

    result = verify_guarded_performance_policy_evidence(payload)

    assert result.valid is False
    assert result.status == "policy_fingerprint_mismatch"


@pytest.mark.parametrize(
    "fingerprint",
    [None, 1, "ABC", "a" * 63, "G" * 64],
)
def test_policy_evidence_verifier_rejects_invalid_fingerprint(
    fingerprint: object,
) -> None:
    payload = verify_guarded_performance_evidence_policy(_evidence(True)).to_dict()
    payload["policy_evidence_fingerprint"] = fingerprint

    result = verify_guarded_performance_policy_evidence(payload)

    assert result.valid is False
    assert result.status == "invalid_policy_fingerprint"
