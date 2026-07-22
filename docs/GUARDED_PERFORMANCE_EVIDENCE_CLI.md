# Guarded performance evidence verification CLI

Use the installed verifier before trusting or archiving a persisted guarded performance-regression decision:

```bash
akilan-verify-performance-evidence \
  artifacts/performance-regression.json \
  --report artifacts/performance-regression-verification.json
```

The command recomputes the repository canonical JSON SHA-256 fingerprint after excluding only `evidence_fingerprint`. It rejects missing files, non-files, malformed JSON, non-object roots, malformed fingerprints, and altered evidence.

## Enforce the recorded decision

Automation that must block on a failed regression decision should add `--require-passed`:

```bash
akilan-verify-performance-evidence \
  artifacts/performance-regression.json \
  --require-passed \
  --report artifacts/performance-regression-verification.json
```

This mode remains read-only. It first verifies evidence integrity, then returns exit code `1` unless the fingerprint-valid report contains the boolean value `passed: true`. A missing, null, string, numeric, or false `passed` value is rejected. The command never recomputes thresholds or converts a failed decision into a passing decision.

Machine-readable output distinguishes:

- `valid`: whether the evidence fingerprint is authentic;
- `recorded_decision`: the persisted `passed` value;
- `require_passed`: whether operational decision enforcement was requested;
- `decision_accepted`: whether both integrity and the requested decision policy passed;
- `operational_status`: `valid`, `accepted`, `recorded_decision_failed`, `recorded_decision_missing`, or the underlying fingerprint-verification status.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | The fingerprint is valid and any requested recorded-decision policy passed. |
| `1` | The source, fingerprint, or requested recorded-decision policy was rejected. |
| `2` | Command-line configuration is invalid. |

Without `--require-passed`, fingerprint validity remains intentionally separate from the recorded decision. A correctly persisted regression report with `passed: false` returns exit code `0` because its integrity is valid. With `--require-passed`, the same authentic failed report returns exit code `1` while retaining `valid: true` in the evidence.

The command does not regenerate performance evidence, reinterpret thresholds, change a failed decision, mutate artifacts, authorize release, or modify the canonical artifact schema.
