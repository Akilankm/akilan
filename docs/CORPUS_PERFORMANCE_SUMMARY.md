# Corpus performance summary

AKILAN benchmark cases already retain per-document timing, memory, byte-volume, throughput, cache, and phase evidence. `summarize_corpus_performance()` adds a deterministic corpus-level view without changing extraction or the canonical artifact schema.

```python
from akilan.benchmark import run_corpus
from akilan.benchmark_summary import summarize_corpus_performance

report = run_corpus(["data/a.pdf", "data/b.pdf"], "artifacts/benchmark")
summary = summarize_corpus_performance(report)
print(summary.to_dict())
```

The summary reports:

- measured case and cache-hit counts;
- cache-hit ratio;
- total elapsed time;
- total source and output bytes;
- total successfully materialized pages;
- aggregate pages and source MiB per second;
- maximum observed process-local Python memory peak;
- deterministic phase-time totals.

Failed cases contribute timing, memory, byte, and phase evidence when available, but do not contribute pages. Peak memory is the maximum individual observation rather than a sum of independent peaks. Empty reports produce an explicit all-zero summary.

This evidence is intended for regression comparison and bottleneck selection. It does not claim operating-system RSS, native PyMuPDF allocation, or concurrent-worker memory usage; those require a separate measurement boundary.
