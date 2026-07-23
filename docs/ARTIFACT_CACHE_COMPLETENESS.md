# Artifact cache completeness

AKILAN separates cache identity from cache reuse. A matching content-addressed key is necessary, but it is not sufficient: the persisted artifact must also be complete and internally valid.

Every successful build now publishes an operational sidecar:

```text
.akilan-cache.json
```

The sidecar is written inside the staging directory only after all canonical artifact files and projections have been generated. The entire staging directory is then atomically published. An interrupted or failed build therefore cannot expose a completion record in the destination.

## Reuse decision

```python
from akilan import validate_artifact_cache

validation = validate_artifact_cache(
    "data/public/complex.pdf",
    "artifacts/complex",
)

if validation.hit:
    print("artifact is safe to reuse")
else:
    print(validation.reasons)
```

A cache hit requires all of the following:

- the completion record exists and contains supported JSON;
- its state is `complete`;
- its source, schema, package, and extraction-configuration identity exactly matches the current request;
- the artifact directory passes the existing structural, path-safety, existence, schema, and cross-file consistency validation.

The validation operation is deterministic and read-only. It never repairs or mutates an artifact. A miss returns concise reasons so callers can rebuild rather than silently accepting partial or stale output.

The sidecar is operational metadata and is deliberately not added to the canonical artifact schema or `artifact_files` contract. PyMuPDF remains the only runtime dependency.
