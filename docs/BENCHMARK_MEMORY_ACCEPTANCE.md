# Benchmark peak-memory acceptance

AKILAN benchmark reports already capture process-local Python allocation peaks through `tracemalloc`. The acceptance layer can now enforce that evidence instead of merely recording it.

```python
from akilan.benchmark_acceptance import BenchmarkThresholds, evaluate_corpus

acceptance = evaluate_corpus(
    report,
    BenchmarkThresholds(max_peak_python_memory_bytes=256 * 1024 * 1024),
)

if not acceptance.passed:
    for violation in acceptance.violations:
        print(violation.rule_id, violation.source, violation.actual)
```

## Contract

- `max_peak_python_memory_bytes=None` leaves the upper bound disabled.
- Configured limits must be non-negative integers; booleans and floating-point approximations are rejected.
- Every passed benchmark case must contain a non-negative integer `peak_python_memory_bytes` value, even when no upper bound is configured.
- A case above the configured limit emits `benchmark-peak-python-memory-v1`.
- Malformed memory evidence emits `benchmark-memory-evidence-valid-v1`.
- Violations remain deterministically ordered with the other case-level acceptance findings.

## Interpretation

The metric measures Python allocations visible to `tracemalloc`; it is not operating-system resident set size and does not claim to capture all native allocations performed by PyMuPDF. It is therefore suitable for deterministic regression budgets within a controlled CI environment, not as a complete machine-memory accounting mechanism.

Cache hits intentionally report zero extraction memory because no extraction is performed. Cold-run memory budgets should be evaluated with cache reuse disabled.
