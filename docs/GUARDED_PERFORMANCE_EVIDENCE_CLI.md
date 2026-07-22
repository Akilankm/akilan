# Guarded performance evidence verification CLI

Use the installed verifier before trusting or archiving a persisted guarded performance-regression decision:

```bash
akilan-verify-performance-evidence \
  artifacts/performance-regression.json \
  --report artifacts/performance-regression-verification.json
```

The command recomputes the repository canonical JSON SHA-256 fingerprint after excluding only `evidence_fingerprint`. It rejects missing files, non-files, malformed JSON, non-object roots, malformed fingerprints, and altered evidence.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | The persisted decision evidence has a valid canonical fingerprint. |
| `1` | The source or fingerprint evidence is invalid. |
| `2` | Command-line configuration is invalid. |

Fingerprint validity is intentionally separate from the recorded decision. A correctly persisted regression report with `passed: false` returns exit code `0` because its integrity is valid; downstream automation must still enforce the report's recorded pass/fail state.

The command is read-only. It does not regenerate performance evidence, reinterpret thresholds, change a failed decision, mutate artifacts, or authorize release.
