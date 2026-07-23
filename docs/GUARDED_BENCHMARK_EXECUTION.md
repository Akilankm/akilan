# Guarded benchmark execution

`run_guarded_corpus()` is the fail-closed execution boundary for callers that must not create benchmark artifacts or cache state when any selected PDF is not extraction-ready.

```python
from akilan.config import ExtractionConfig
from akilan.guarded_benchmark import BenchmarkSourceGuardError, run_guarded_corpus

try:
    report = run_guarded_corpus(
        ["data/report-a.pdf", "data/report-b.pdf"],
        "artifacts/benchmark",
        config=ExtractionConfig(overwrite=True),
        use_cache=False,
    )
except BenchmarkSourceGuardError as exc:
    evidence = exc.report.to_dict()
    raise RuntimeError(evidence) from exc
```

## Contract

Before delegating to the existing benchmark runner, the boundary:

1. materializes the exact source iterable once, so generators are supported;
2. normalizes, deduplicates, and deterministically orders source paths;
3. runs the existing read-only PDF preflight checks;
4. rejects empty source sets and any missing, malformed, password-protected, zero-page, or otherwise unreadable PDF;
5. creates no output root, canonical artifact, or benchmark cache marker when rejected.

The raised `BenchmarkSourceGuardError` retains the complete deterministic `BenchmarkSourceGuardReport`, including per-source statuses, aggregate counts, and the evidence fingerprint.

## Compatibility

The existing `run_corpus()` API retains its per-file failure-isolation semantics for callers that deliberately need a mixed success/failure report. `run_guarded_corpus()` is an additive operational boundary for enterprise and CI workflows that require all-or-nothing source readiness before benchmark state is created.

Encrypted benchmark execution remains fail-closed. Although preflight can authenticate encrypted PDFs, the current benchmark runner does not yet forward per-source credentials into extraction. This boundary therefore does not accept passwords and will not create a misleading successful preflight followed by an extraction failure.

PyMuPDF remains the only runtime dependency. This change does not alter the canonical artifact schema.
