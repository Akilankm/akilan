# Benchmark cache audit reporting

`audit_benchmark_cache()` validates every persisted benchmark cache entry below a root directory and produces deterministic corpus-level evidence.

```python
from akilan.benchmark_cache_audit import (
    audit_benchmark_cache,
    write_benchmark_cache_audit_report,
)

report = audit_benchmark_cache("artifacts/benchmark")
write_benchmark_cache_audit_report(
    report,
    "artifacts/benchmark-cache-audit.json",
)

if not report.passed:
    raise SystemExit(report.to_dict())
```

## Discovery contract

A directory is treated as a benchmark cache entry only when it contains `.akilan-benchmark-cache.json`. Entries are discovered recursively and emitted in stable relative-path order. Unrelated files and directories are ignored.

Each entry is validated through the existing `validate_benchmark_cache_entry()` boundary, including marker contract, request identity shape, cached metrics, canonical artifact-directory integrity, persisted source identity, page count, and artifact fingerprint consistency.

An empty or missing cache root fails closed with zero entries and `passed == False`. A path that exists but is not a directory raises `NotADirectoryError`.

## Evidence contract

The report contains:

- total, valid, and invalid entry counts;
- a corpus-level pass/fail decision;
- every entry's relative artifact path;
- complete stable violation evidence;
- a SHA-256 `report_fingerprint` over the report payload excluding the fingerprint itself.

The canonical JSON fingerprint contract sorts keys recursively, uses compact separators, preserves Unicode as UTF-8, and is independent of source formatting or mapping insertion order.

The audit is read-only. It does not repair, delete, rewrite, or rebuild cache entries. The report is operational CI evidence and does not alter the canonical artifact schema. PyMuPDF remains the only runtime dependency.
