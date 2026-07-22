# Guarded performance policy evidence CLI

`akilan-verify-performance-policy-evidence` verifies persisted operational policy evidence produced after guarded performance-regression evidence has been authenticated and evaluated.

## Integrity-only verification

```bash
akilan-verify-performance-policy-evidence \
  artifacts/performance-policy.json \
  --report artifacts/performance-policy-verification.json
```

Exit code `0` means the canonical policy-evidence fingerprint is valid. The recorded policy decision may still be rejected.

## Require operational acceptance

```bash
akilan-verify-performance-policy-evidence \
  artifacts/performance-policy.json \
  --require-accepted \
  --report artifacts/performance-policy-verification.json
```

With `--require-accepted`, exit code `0` requires both:

1. a valid `policy_evidence_fingerprint`; and
2. a protected boolean `decision_accepted: true`.

The command never recomputes performance thresholds, changes the policy, or converts rejected evidence into accepted evidence.

## Exit codes

- `0`: fingerprint-valid evidence satisfying the requested acceptance policy;
- `1`: missing, malformed, fingerprint-invalid, or policy-rejected evidence;
- `2`: invalid command configuration reported by `argparse`.

## Stable operational statuses

- `valid`: authentic evidence accepted in integrity-only mode;
- `accepted`: authentic evidence records `decision_accepted: true` when acceptance is required;
- `recorded_policy_rejected`: authentic evidence records `decision_accepted: false`;
- `recorded_policy_decision_missing`: authentic evidence does not contain a boolean policy decision;
- `invalid_policy_fingerprint`: the fingerprint is missing or malformed;
- `policy_fingerprint_mismatch`: protected policy evidence was altered after fingerprinting.

## Automation boundary

Use integrity-only mode for audit ingestion where authentic rejected decisions must remain consumable. Use `--require-accepted` at deployment, publication, or benchmark-promotion boundaries that must fail closed when the recorded policy rejected the evidence.
