# Content-addressed benchmark cache

`run_corpus()` reuses a completed benchmark artifact only when all extraction-relevant inputs match exactly.

## Cache identity

The cache key is a SHA-256 digest over:

- the complete source PDF byte digest;
- every `ExtractionConfig` field;
- the installed AKILAN package version;
- the benchmark cache-format version.

The marker is stored as `.akilan-benchmark-cache.json` inside the completed case artifact. It contains only the identity and deterministic artifact metrics. The canonical `document.json` and page artifacts remain the source of truth.

## Safety properties

- Missing, stale, malformed, or incompatible markers are ignored.
- Failed extractions never produce reusable cache entries.
- Marker publication uses a same-directory temporary file followed by an atomic replacement.
- Cache reuse never mutates the completed artifact.
- `use_cache=False` forces extraction and refreshes the completed artifact through the builder's atomic publication contract.
- A cache hit is explicit in benchmark output as `performance.cache_hit=true`.

## Usage

```python
from pathlib import Path

from akilan.benchmark import run_corpus
from akilan.config import ExtractionConfig

pdfs = sorted(Path("data").rglob("*.pdf"))
report = run_corpus(
    pdfs,
    "artifacts/benchmark",
    config=ExtractionConfig(overwrite=True),
)
```

Force a clean benchmark run when measuring extraction throughput:

```python
report = run_corpus(
    pdfs,
    "artifacts/benchmark",
    config=ExtractionConfig(overwrite=True),
    use_cache=False,
)
```

## Measurement interpretation

A cache hit reports the lookup duration, zero Python extraction-memory allocation, and current on-disk artifact size. Do not mix cache-hit throughput with cold extraction throughput when publishing performance comparisons. Filter cases using `performance.cache_hit`.

## Deliberate limits

This cache is scoped to corpus benchmarking. It does not yet provide shared cross-machine cache storage, page-level incremental rebuilds, eviction, locking between concurrent writers, or artifact deserialization through the public builder API. Those require separate reviewed designs.