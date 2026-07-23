# Benchmark cache fingerprint verification

Benchmark cache reuse is valid only when the persisted canonical document still matches the fingerprint recorded when the benchmark case was measured.

## Why this check exists

A syntactically valid SHA-256 value in `.akilan-benchmark-cache.json` is not evidence that the current artifact content is unchanged. A canonical artifact may remain schema-valid after accidental edits, manual rewrites, or storage corruption.

`validate_benchmark_cache_entry()` therefore recomputes the SHA-256 fingerprint from the parsed `document.json` mapping using the same canonical JSON representation as `artifact_fingerprint()`:

- keys sorted recursively;
- compact separators;
- UTF-8 encoding;
- non-ASCII text preserved.

The recomputed digest must exactly match:

```text
$.cache.metrics.artifact_fingerprint
```

A mismatch produces the stable rule:

```text
benchmark-cache-integrity-v1
```

and the cache entry becomes a normal miss in `run_corpus()`.

## Safety boundary

The check is:

- read-only;
- deterministic;
- independent of JSON indentation and key order;
- additive to schema, manifest, page-file, source-digest, and page-count validation;
- outside the canonical artifact schema.

No artifact is repaired or deleted automatically. Rebuilding remains the responsibility of the existing benchmark orchestration path.
