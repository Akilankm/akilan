# Benchmark elapsed-time acceptance

AKILAN benchmark reports record wall-clock elapsed time for each corpus case. The acceptance layer can enforce an optional per-case budget so performance regressions fail with deterministic evidence instead of remaining observational only.

```python
from akilan.benchmark_acceptance import BenchmarkThresholds, evaluate_corpus

acceptance = evaluate_corpus(
    report,
    BenchmarkThresholds(max_elapsed_seconds=30.0),
)
```

## Contract

- `max_elapsed_seconds=None` keeps the budget disabled for backward compatibility.
- Configured limits must be finite, non-negative numeric values; booleans are rejected.
- Every passed benchmark case must contain finite, non-negative `elapsed_seconds` evidence.
- A case above the configured budget emits `benchmark-elapsed-time-v1`.
- Malformed elapsed-time evidence emits `benchmark-elapsed-time-evidence-valid-v1`.
- Findings retain deterministic ordering with all other case-level acceptance violations.

## Interpretation

Elapsed time is wall-clock evidence for one benchmark case. It is sensitive to machine load, filesystem state, cache state, and runner class. Use `--no-cache` for cold-extraction budgets, establish limits on a controlled runner, and leave reasonable headroom for normal CI variance. This boundary is intended to detect material regressions, not microbenchmark noise.
