# Validated artifact loading

Use `load_artifact_directory()` when a persisted AKILAN artifact is entering a downstream pipeline, cache, archive, notebook, or service boundary.

```python
from akilan import load_artifact_directory

document = load_artifact_directory("artifacts/document")
print(document["source"]["sha256"])
print(document["statistics"])
```

The loader validates the complete directory before returning canonical document data. Validation includes the manifest contract, safe relative paths, declared-file existence, canonical artifact structure, page identity, and JSON parsing.

A malformed, incomplete, or path-unsafe directory raises `ArtifactSchemaError` with aggregated JSON-style violation paths. The loader is read-only: it never repairs, deletes, downloads, or rewrites artifact files.

The canonical document path is resolved from `manifest.json`; callers should not assume that it is always named `document.json`.

## Recommended boundary pattern

```python
from akilan import ArtifactSchemaError, load_artifact_directory

try:
    document = load_artifact_directory(artifact_dir)
except ArtifactSchemaError as exc:
    quarantine(artifact_dir, reason=str(exc))
    raise

consume(document)
```

This API adds no runtime dependency. PyMuPDF remains AKILAN's only runtime dependency.
