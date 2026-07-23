# Benchmark memory budget CLI

The benchmark CLI can enforce the existing per-case peak Python allocation boundary without requiring custom Python orchestration.

```bash
akilan benchmark data \
  --output-root artifacts/benchmark \
  --report artifacts/benchmark/report.json \
  --acceptance-report artifacts/benchmark/acceptance.json \
  --max-peak-python-memory-bytes 268435456 \
  --no-cache
```

## Contract

- The option is disabled when omitted, preserving existing benchmark behavior.
- The value is a non-negative integer number of bytes.
- Invalid negative values fail before extraction through `BenchmarkThresholds` validation.
- Every passed case is evaluated independently against the configured limit.
- Exceeding the budget emits `benchmark-peak-python-memory-v1` in the acceptance evidence.
- Use `--no-cache` when establishing a cold-extraction memory budget because a cache hit performs no extraction.

The metric is produced by `tracemalloc` and represents Python allocations visible to that instrumentation. It is not a complete operating-system RSS measurement and does not include every native allocation made inside PyMuPDF.
