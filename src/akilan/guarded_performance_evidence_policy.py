"""Operational policy checks for persisted guarded performance evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .canonical_json import canonical_json_fingerprint
from .guarded_performance_regression import (
    GuardedPerformanceEvidenceVerification,
    verify_guarded_performance_regression_evidence,
)

_POLICY_FINGERPRINT_FIELD = "policy_evidence_fingerprint"


@dataclass(frozen=True, slots=True)
class GuardedPerformanceEvidencePolicyVerification:
    """Integrity and recorded-decision policy result for persisted evidence."""

    integrity: GuardedPerformanceEvidenceVerification
    require_passed: bool
    recorded_decision: bool | None
    decision_accepted: bool
    operational_status: str

    def _protected_payload(self) -> dict[str, Any]:
        """Return the canonical payload protected by the policy fingerprint."""

        return {
            **self.integrity.to_dict(),
            "operational_status": self.operational_status,
            "require_passed": self.require_passed,
            "recorded_decision": self.recorded_decision,
            "decision_accepted": self.decision_accepted,
        }

    @property
    def policy_evidence_fingerprint(self) -> str:
        """Return the canonical SHA-256 identity of this policy decision."""

        return canonical_json_fingerprint(self._protected_payload())

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic, tamper-evident machine-readable policy evidence."""

        payload = self._protected_payload()
        return {
            **payload,
            _POLICY_FINGERPRINT_FIELD: canonical_json_fingerprint(payload),
        }


@dataclass(frozen=True, slots=True)
class GuardedPerformancePolicyEvidenceVerification:
    """Verification result for persisted policy-decision evidence."""

    valid: bool
    status: str
    expected_fingerprint: str | None
    actual_fingerprint: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic verification evidence."""

        return {
            "valid": self.valid,
            "status": self.status,
            "expected_fingerprint": self.expected_fingerprint,
            "actual_fingerprint": self.actual_fingerprint,
        }


def verify_guarded_performance_evidence_policy(
    evidence: Mapping[str, Any],
    *,
    require_passed: bool = False,
) -> GuardedPerformanceEvidencePolicyVerification:
    """Verify evidence integrity and optionally require its recorded pass decision.

    Fingerprint verification always runs first. The function never recomputes
    thresholds, changes the recorded decision, or treats invalid evidence as accepted.
    """

    integrity = verify_guarded_performance_regression_evidence(evidence)
    raw_decision = evidence.get("passed")
    recorded_decision = raw_decision if isinstance(raw_decision, bool) else None

    if not integrity.valid:
        operational_status = integrity.status
        decision_accepted = False
    elif not require_passed:
        operational_status = "valid"
        decision_accepted = True
    elif recorded_decision is True:
        operational_status = "accepted"
        decision_accepted = True
    elif recorded_decision is False:
        operational_status = "recorded_decision_failed"
        decision_accepted = False
    else:
        operational_status = "recorded_decision_missing"
        decision_accepted = False

    return GuardedPerformanceEvidencePolicyVerification(
        integrity=integrity,
        require_passed=require_passed,
        recorded_decision=recorded_decision,
        decision_accepted=decision_accepted,
        operational_status=operational_status,
    )


def verify_guarded_performance_policy_evidence(
    evidence: Mapping[str, Any],
) -> GuardedPerformancePolicyEvidenceVerification:
    """Verify the fingerprint of persisted policy-decision evidence.

    Only the policy fingerprint field is excluded from the protected payload. The
    function verifies evidence authenticity; it does not reinterpret acceptance.
    """

    raw_fingerprint = evidence.get(_POLICY_FINGERPRINT_FIELD)
    if (
        not isinstance(raw_fingerprint, str)
        or len(raw_fingerprint) != 64
        or raw_fingerprint.lower() != raw_fingerprint
        or any(character not in "0123456789abcdef" for character in raw_fingerprint)
    ):
        return GuardedPerformancePolicyEvidenceVerification(
            valid=False,
            status="invalid_policy_fingerprint",
            expected_fingerprint=None,
            actual_fingerprint=raw_fingerprint if isinstance(raw_fingerprint, str) else None,
        )

    protected_payload = {
        key: value for key, value in evidence.items() if key != _POLICY_FINGERPRINT_FIELD
    }
    expected_fingerprint = canonical_json_fingerprint(protected_payload)
    valid = expected_fingerprint == raw_fingerprint
    return GuardedPerformancePolicyEvidenceVerification(
        valid=valid,
        status="valid" if valid else "policy_fingerprint_mismatch",
        expected_fingerprint=expected_fingerprint,
        actual_fingerprint=raw_fingerprint,
    )
