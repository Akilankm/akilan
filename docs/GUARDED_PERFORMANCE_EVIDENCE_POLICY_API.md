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

## Stable operational statuses

- `valid`: authentic evidence accepted in integrity-only mode;
- `accepted`: authentic evidence records `passed: true` under enforcement;
- `recorded_decision_failed`: authentic evidence records `passed: false`;
- `recorded_decision_missing`: the protected decision is absent or not boolean;
- `invalid_fingerprint`: fingerprint syntax is invalid;
- `fingerprint_mismatch`: protected evidence was altered or substituted.

The returned payload retains the underlying expected and actual fingerprints, recorded decision, requested policy, and final `decision_accepted` result for deterministic audit evidence.
