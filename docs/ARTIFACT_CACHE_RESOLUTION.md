# Artifact cache resolution

AKILAN separates cache validation from artifact consumption. `validate_artifact_cache()` explains whether an existing directory is reusable; `resolve_artifact_cache()` performs that validation and returns the canonical `document.json` payload only when the cache is complete and identity-equivalent.

```python
from akilan import ExtractionConfig, resolve_artifact_cache

resolution = resolve_artifact_cache(
    "data/public/complex.pdf",
    "artifacts/complex",
    ExtractionConfig(render_pages=True),
)

if resolution.hit:
    document = resolution.artifact
else:
    print(resolution.reasons)
```

## Safety contract

A resolution is a hit only when all of the following are true:

1. the operational completion record exists and declares a complete artifact;
2. source digest, schema version, package version, and semantic extraction configuration match;
3. the complete persisted artifact directory passes integrity validation;
4. the canonical document payload is revalidated immediately before loading.

The final validation closes the time-of-check/time-of-use gap where files could change between the cache decision and consumption.

## Miss behavior

Cache misses are normal control flow. They return:

- `hit == False`;
- `artifact is None`;
- deterministic reasons suitable for logs and orchestration decisions.

The resolver never repairs, deletes, or rewrites an artifact. The returned mapping is detached from disk, so caller mutation cannot alter the persisted cache.

## Scope

This API establishes the safe reuse boundary. It does not yet make `PDFArtifactBuilder.build()` skip extraction automatically; orchestration layers can use the resolver before invoking a build. This keeps the existing builder return type and overwrite semantics stable while incremental caching evolves under issue #7.
