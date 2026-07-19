# Cache-aware artifact construction

`build_or_resolve_artifact()` is the production orchestration boundary for consumers that want validated reuse without duplicating cache-control logic.

```python
from akilan import ExtractionConfig, build_or_resolve_artifact

result = build_or_resolve_artifact(
    "data/public/complex.pdf",
    "artifacts/complex",
    ExtractionConfig(overwrite=True),
)

print(result.cache_hit)
print(result.identity.key)
document = result.artifact
```

## Decision sequence

1. Build the deterministic request identity from source bytes, schema version, package version, and semantic extraction configuration.
2. Require a complete cache record and full artifact-directory validation.
3. Return the validated canonical document payload immediately on a hit.
4. On a miss, build through `PDFArtifactBuilder` using its staging and atomic publication guarantees.
5. Revalidate and reload the newly published directory before returning it.
6. Fail closed if the fresh artifact cannot pass the same consumption boundary.

Directory presence is never treated as a cache hit. A stale, malformed, partial, or identity-mismatched directory is not returned.

## Replacement policy

The function preserves the existing output-protection contract. A cache miss does not silently delete non-equivalent output. Set `ExtractionConfig(overwrite=True)` when the caller explicitly permits replacement of a stale artifact directory.

## Result contract

`ArtifactBuildResolution` returns:

- `artifact`: detached canonical `document.json` content;
- `cache_hit`: whether extraction was skipped;
- `rebuilt`: the inverse operational decision;
- `identity`: the exact request identity;
- `prior_miss_reasons`: deterministic evidence explaining why a build was required.

`to_dict()` intentionally excludes the potentially large artifact payload, making it suitable for logs and CI evidence.

## Compatibility

- PyMuPDF remains the only runtime dependency.
- `PDFArtifactBuilder.build()` and `build_artifact()` retain their existing return contracts.
- The completion record remains operational metadata outside the canonical artifact schema.
- No cache hit bypasses artifact-directory integrity validation.
