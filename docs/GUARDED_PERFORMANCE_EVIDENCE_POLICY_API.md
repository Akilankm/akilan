# Guarded performance evidence policy API

Use this boundary when a Python consumer must both verify persisted guarded performance-regression evidence and optionally enforce its recorded decision.

```python
from akilan.guarded_performance_evidence_policy import (
    verify_guarded_performance_evidence_policy,
)

verification = verify_guarded_performance_evidence_policy(
    persisted_evidence,
    require_passed=True,
)

if not verification.decision_accepted:
    raise RuntimeError(verification.to_dict())
```

## Contract

Fingerprint verification always runs before decision policy. Invalid or altered evidence is never accepted, even when its visible `passed` field is `true`.

With `require_passed=False`, authentic evidence is accepted regardless of whether it records a pass or failure. This mode verifies audit integrity only.

With `require_passed=True`, evidence is accepted only when:

1. the canonical SHA-256 fingerprint is valid; and
2. the protected `passed` field is the JSON boolean `true`.

Missing, null, numeric, and string decision values fail closed. The API never recomputes thresholds, changes the recorded result, or converts a failed regression into a pass.

## Tamper-evident policy decision

`verification.to_dict()` includes `policy_evidence_fingerprint`, a canonical SHA-256 fingerprint covering the complete policy result:

- underlying regression-evidence verification;
- requested `require_passed` policy;
- protected recorded decision;
- final `decision_accepted` result;
- stable operational status.

The fingerprint field is excluded from its own protected payload, so independent consumers can recompute it deterministically.

Persisted policy evidence can be verified without re-running regression thresholds or policy evaluation:

```python
from akilan.guarded_performance_evidence_policy import (
    verify_guarded_performance_policy_evidence,
)

integrity = verify_guarded_performance_policy_evidence(persisted_policy_evidence)
if not integrity.valid:
    raise RuntimeError(integrity.to_dict())
```

Verification checks authenticity only. Consumers must still enforce the protected `decision_accepted` value according to their workflow.

## Stable operational statuses

- `valid`: authentic evidence accepted in integrity-only mode;
- `accepted`: authentic evidence records `passed: true` under enforcement;
- `recorded_decision_failed`: authentic evidence records `passed: false`;
- `recorded_decision_missing`: the protected decision is absent or not boolean;
- `invalid_fingerprint`: regression-evidence fingerprint syntax is invalid;
- `fingerprint_mismatch`: protected regression evidence was altered or substituted.

Policy-evidence verification returns:

- `valid` for an authentic policy payload;
- `invalid_policy_fingerprint` for a missing or malformed policy fingerprint;
- `policy_fingerprint_mismatch` when any protected policy field changed.

The returned payload retains expected and actual fingerprints for deterministic audit evidence.
