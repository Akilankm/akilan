# Safe benchmark cache reuse

`run_corpus()` treats a benchmark cache entry as reusable only after validating both its marker and its persisted artifact directory.

A cache hit requires all of the following:

- the benchmark request identity matches the current source bytes, extraction configuration, package version, and cache format;
- `.akilan-benchmark-cache.json` is valid JSON with the required metric fields;
- the canonical artifact directory passes full integrity validation;
- cached source SHA-256 and page count agree with `document.json`;
- the cached artifact fingerprint has valid lowercase SHA-256 syntax.

Any violation is handled as a normal cache miss. The benchmark runner rebuilds through `PDFArtifactBuilder` using the caller's existing overwrite policy and then publishes a fresh marker.

This prevents a stale marker from masking partial deletion, manual modification, interrupted copies, or metric drift. It also keeps benchmark execution resilient: invalid cache state is not reported as an extraction failure when a safe rebuild can recover it.

```python
from akilan import ExtractionConfig
from akilan.benchmark import run_corpus

report = run_corpus(
    ["data/example.pdf"],
    "artifacts/benchmark",
    config=ExtractionConfig(overwrite=True),
)

case = report.cases[0]
print(case.performance.cache_hit)
```

Set `use_cache=False` to force a cold extraction. Cache validation and reuse do not modify the canonical artifact schema and introduce no runtime dependency beyond PyMuPDF.
