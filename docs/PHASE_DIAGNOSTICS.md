# Benchmark phase diagnostics

AKILAN corpus reports expose process-local phase timings under `performance.phase_seconds` without modifying the canonical document artifact schema.

## Phases

| Phase | Meaning |
|---|---|
| `cache_lookup` | Source/configuration identity calculation and cache-marker lookup. |
| `extraction` | PDF opening, page extraction, inference, serialization, and atomic publication. |
| `measurement` | Deterministic artifact coverage metrics and fingerprinting. |
| `cache_write` | Atomic publication of a successful benchmark cache marker. Present only when caching is enabled and writable. |
| `total` | End-to-end case duration measured by the corpus harness. |

A cache hit intentionally reports only `cache_lookup` and `total`; it never fabricates extraction or measurement work. Failed cases retain the completed phase evidence plus `total`, and an `extraction` duration covering the interrupted extraction attempt.

## Interpretation

Timings use `time.perf_counter()` and are rounded to six decimal places. They are diagnostic evidence, not deterministic artifact content. Compare repeated warm and cold runs on equivalent hardware before treating a phase as a bottleneck.

The sum of named phases can be less than `total` because orchestration, object construction, memory sampling, and exception handling are not assigned to a named phase. It must never materially exceed `total` except for sub-microsecond rounding effects.

## Example

```python
from pathlib import Path

from akilan.benchmark import run_corpus
from akilan.config import ExtractionConfig

report = run_corpus(
    Path("data").rglob("*.pdf"),
    "artifacts/benchmark",
    config=ExtractionConfig(overwrite=True),
    use_cache=False,
)

for case in report.cases:
    print(case.source, case.performance.phase_seconds if case.performance else {})
```

Use `use_cache=False` for cold extraction profiling. Use the default cache behavior to quantify reuse overhead separately.
