# Benchmark cache marker contract

AKILAN treats `.akilan-benchmark-cache.json` as operational evidence, not as part of the canonical document artifact schema.

A marker is reusable only when all of the following hold:

- `cache_format_version` is the supported integer version (`1`);
- `identity` is a lowercase 64-character SHA-256 digest and, when supplied by the caller, matches the expected benchmark request identity;
- `metrics` is an object containing `source_sha256`, `page_count`, and `artifact_fingerprint`;
- both digest fields are lowercase 64-character SHA-256 values;
- `page_count` is a non-negative integer and not a boolean;
- cached source identity and page count agree with `document.json`;
- the complete canonical artifact directory passes integrity validation.

Unsupported, malformed, incomplete, or inconsistent markers are normal cache misses. The validator is read-only: it never repairs, deletes, or rewrites cache state.

```python
from akilan import validate_benchmark_cache_entry

violations = validate_benchmark_cache_entry(
    "artifacts/benchmark/example-case",
    expected_identity="<benchmark-request-sha256>",
)

if violations:
    for violation in violations:
        print(violation.to_dict())
```

Every finding uses the stable rule ID `benchmark-cache-integrity-v1` and a deterministic JSON-style path suitable for CI evidence.
