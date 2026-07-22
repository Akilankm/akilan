# Guarded performance regression API

Use `compare_guarded_corpus_performance()` when an automated performance decision must be bound to the exact PDF source set accepted by the benchmark source guard.

```python
from akilan.guarded_performance_regression import compare_guarded_corpus_performance

report = compare_guarded_corpus_performance(
    current_summary,
    approved_baseline,
    current_source_fingerprint=current_guard.fingerprint,
    baseline_source_fingerprint=approved_guard.fingerprint,
)

if not report.passed:
    raise RuntimeError(report.to_dict())
```

The API validates both fingerprints as lowercase 64-character SHA-256 values, preserves the exact baseline and current identities in evidence, and emits `performance-source-identity-v1` when they differ. Performance and identity violations are returned in deterministic metric order.

This boundary is read-only. It does not mutate benchmark evidence, artifacts, source PDFs, thresholds, or the canonical artifact schema. PyMuPDF remains the only runtime dependency.
