# Benchmark source guard

`guard_benchmark_sources()` is the fail-closed handoff between PDF preflight and benchmark execution.

It accepts the exact source paths selected by a caller, normalizes and deduplicates them, runs the established read-only PDF preflight boundary, and returns deterministic machine-readable evidence before any benchmark artifact or cache entry is created.

```python
from akilan.benchmark_source_guard import guard_benchmark_sources

sources = ["data/report-a.pdf", "data/report-b.pdf"]
report = guard_benchmark_sources(sources)

if not report.accepted:
    raise RuntimeError(report.to_dict())
```

## Contract

The guard:

- fails closed for an empty source set;
- reports missing, malformed, password-protected, zero-page, and otherwise rejected PDFs;
- normalizes, deduplicates, and deterministically orders source paths;
- supports passwords keyed by supplied or normalized absolute path;
- never persists password values;
- emits stable accepted, rejected, total, and per-status counts;
- emits a canonical SHA-256 evidence fingerprint;
- never creates artifacts, writes benchmark caches, repairs PDFs, or mutates source files.

The guard intentionally does not run extraction. Callers should proceed to `run_corpus()` only when `report.accepted` is `True`.
