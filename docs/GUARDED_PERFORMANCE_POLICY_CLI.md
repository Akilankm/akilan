# Guarded performance policy decision CLI

`akilan-performance-policy` converts persisted guarded performance-regression evidence into a deterministic, tamper-evident operational policy decision.

```bash
akilan-performance-policy \
  artifacts/performance-regression.json \
  --require-passed \
  --report artifacts/performance-policy.json
```

## Decision sequence

1. Load a JSON object from the supplied regression-evidence path.
2. Verify its canonical `evidence_fingerprint` before reading the recorded decision.
3. Apply the requested policy without recomputing thresholds or modifying the recorded result.
4. Persist the complete decision with `policy_evidence_fingerprint`.

With `--require-passed`, authentic evidence is accepted only when it records boolean `passed: true`. Authentic evidence recording a regression is still persisted for audit, but the command exits with status `1`.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Policy evidence was persisted and the decision was accepted. |
| `1` | Source evidence was missing, malformed, fingerprint-invalid, or policy-rejected. |
| `2` | CLI configuration was invalid. |

## Safety properties

- The source regression report is never overwritten.
- Missing or malformed source evidence creates no policy report.
- Fingerprint-valid rejected decisions are persisted rather than hidden.
- The command does not rerun benchmarks, reinterpret thresholds, or mutate artifacts.
- PyMuPDF remains the only runtime dependency.

Persisted policy evidence can be independently checked with:

```bash
akilan-verify-performance-policy-evidence \
  artifacts/performance-policy.json \
  --require-accepted
```
