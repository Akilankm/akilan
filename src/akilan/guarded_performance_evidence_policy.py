"""Operational policy checks for persisted guarded performance evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from .guarded_performance_regression import (
    GuardedPerformanceEvidenceVerification,
    verify_guarded_performance_regression_evidence,
)


@dataclass(frozen=True, slots=True)
class GuardedPerformanceEvidencePolicyVerification:
    """Integrity and recorded-decision policy result for persisted evidence."""

    integrity: GuardedPerformanceEvidenceVerification
    require_passed: bool
    recorded_decision: bool | None
    decision_accepted: bool
    operational_status: str

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic machine-readable policy evidence."""

        return {
            **self.integrity.to_dict(),
            "operational_status": self.operational_status,
            "require_passed": self.require_passed,
            "recorded_decision": self.recorded_decision,
            "decision_accepted": self.decision_accepted,
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
