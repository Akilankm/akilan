# Guarded performance regression API

Use `compare_guarded_corpus_performance()` when an automated performance decision must be bound to the exact PDF source set accepted by the benchmark source guard and, when available, the exact execution context used for both runs.

```python
from akilan.guarded_performance_regression import compare_guarded_corpus_performance

report = compare_guarded_corpus_performance(
    current_summary,
    approved_baseline,
    current_source_fingerprint=current_guard.fingerprint,
    baseline_source_fingerprint=approved_guard.fingerprint,
    current_execution_identity=current_execution_identity,
    baseline_execution_identity=approved_execution_identity,
)

if not report.passed:
    raise RuntimeError(report.to_dict())
```

The API validates source fingerprints as lowercase 64-character SHA-256 values. Execution identities are optional for backward compatibility, but they are an all-or-nothing pair: supplying only one raises `ValueError`.

When both execution identities are supplied, the comparison fails closed unless:

- both identity fingerprints validate against their represented runtime and extraction configuration;
- both identities have the same canonical fingerprint;
- the guarded source fingerprints match;
- the benchmark workload counters match;
- no configured performance threshold is violated.

Stable blocking rules are:

- `performance-source-identity-v1` for different guarded PDF source sets;
- `performance-execution-identity-v1` for invalid, tampered, or different execution contexts.

Performance, source, and execution-identity violations are emitted in deterministic metric order. The evidence includes exact baseline/current fingerprints and validity flags without exposing volatile host data.

## Decision evidence fingerprint

Every report exposes `evidence_fingerprint`, a lowercase SHA-256 digest calculated from the complete canonical decision payload:

- baseline and current performance summaries;
- threshold evaluation and workload-equivalence evidence;
- guarded source identities;
- optional execution identities and validity flags;
- final pass/fail state;
- stable ordered violations.

```python
evidence = report.to_dict()
assert evidence["evidence_fingerprint"] == report.evidence_fingerprint
```

The fingerprint field itself is excluded from the protected payload. Persist the complete `to_dict()` result to bind an audit record to the exact decision evidence.

## Verify persisted evidence

Consumers should verify persisted evidence before trusting its decision fields:

```python
from akilan.guarded_performance_regression import (
    verify_guarded_performance_regression_evidence,
)

verification = verify_guarded_performance_regression_evidence(persisted_evidence)
if not verification.valid:
    raise RuntimeError(verification.to_dict())
```

The verifier:

- requires a lowercase 64-character SHA-256 `evidence_fingerprint`;
- removes only that fingerprint field from the protected payload;
- recomputes the canonical JSON fingerprint;
- returns `valid`, `invalid_fingerprint`, or `fingerprint_mismatch`;
- exposes expected and actual fingerprints for deterministic audit evidence;
- never reinterprets a failed performance decision as passing.

Fingerprint verification proves that the persisted canonical decision payload has not changed since it was produced. It does not replace source-guard validation, execution-identity validation, workload-equivalence checks, or threshold evaluation.

This boundary is read-only. It does not mutate benchmark evidence, artifacts, source PDFs, thresholds, execution identities, or the canonical artifact schema. PyMuPDF remains the only runtime dependency.
