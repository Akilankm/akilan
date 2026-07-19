# Benchmark cache integrity

AKILAN benchmark cache markers are operational evidence, not proof that a persisted artifact is complete. A marker can survive manual deletion, interrupted copying, or accidental modification of canonical files.

Use the read-only validation boundary before treating an existing benchmark directory as reusable:

```python
from akilan import validate_benchmark_cache_entry

violations = validate_benchmark_cache_entry(
    "artifacts/benchmark/example-case",
    expected_identity="optional-request-identity",
)

if violations:
    for violation in violations:
        print(violation.to_dict())
```

A valid entry requires:

- a readable JSON `.akilan-benchmark-cache.json` marker;
- a non-empty benchmark request identity;
- required cached metric fields;
- a complete artifact directory that passes canonical directory validation;
- cached source SHA-256 and page count matching `document.json`;
- a syntactically valid lowercase SHA-256 artifact fingerprint.

Every finding uses the stable rule identifier:

```text
benchmark-cache-integrity-v1
```

The validator is deterministic and does not repair, delete, or rewrite files. Callers should treat any violation as a cache miss and rebuild through the normal benchmark path. This API deliberately does not change the canonical artifact schema or cache identity format.
