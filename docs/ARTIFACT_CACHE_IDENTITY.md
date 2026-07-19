# Artifact cache identity

AKILAN exposes a deterministic cache-key boundary for extraction requests:

```python
from akilan.cache_identity import build_artifact_cache_identity
from akilan.config import ExtractionConfig

identity = build_artifact_cache_identity(
    "data/public/complex.pdf",
    ExtractionConfig(render_pages=True),
)
print(identity.key)
```

The key is SHA-256 over canonical JSON containing:

- source file SHA-256;
- canonical artifact schema version;
- AKILAN package version;
- all extraction configuration values that can change artifact content.

`overwrite` is excluded because it controls publication behavior rather than artifact semantics. Tuple-based page selections are normalized to JSON arrays before hashing.

## Operational contract

A cache hit is valid only when the complete identity matches. Consumers must still verify that the cached artifact is complete and passes directory and semantic validation before reuse. This API defines identity only; it does not silently reuse or mutate artifacts.

Changing source bytes, schema version, package version, page selection, rendering, or any extraction option produces a different key. The result is immutable and can be serialized with `to_dict()`.

This increment introduces no runtime dependency and no canonical artifact-schema change.
