# Persisted Artifact Cross-File Consistency

AKILAN artifacts intentionally duplicate a small amount of indexing information across `manifest.json`, `document.json`, and per-page JSON files. This improves operational discovery, but it also creates a risk: a partial copy, manual edit, interrupted synchronization, or stale cache can leave every individual JSON file structurally valid while the directory as a whole is contradictory.

`validate_artifact_directory()` therefore validates both file-level contracts and cross-file identity.

## Guarantees

For a valid persisted artifact directory:

- the manifest's `schema_version`, `generator`, `source`, `document`, and `statistics` fields exactly match `document.json`;
- all artifact-file indexes except `document_json` exactly match the canonical document index;
- `manifest.json` remains authoritative for locating a deliberately relocated canonical document file;
- each manifest page index agrees with the corresponding canonical page for page number, label, JSON path, Markdown path, render path, and metrics;
- the number of declared page JSON files agrees with the number of canonical pages;
- every declared page path matches the corresponding canonical page's `json_path`;
- each per-page JSON document exactly matches its canonical page object in `document.json`.

The comparison is deterministic and dependency-free. It does not repair files or choose one copy as authoritative when evidence conflicts.

## Usage

```python
from akilan import validate_artifact_directory

validate_artifact_directory("artifacts/document")
```

For diagnostics without immediately raising:

```python
violations = validate_artifact_directory(
    "artifacts/document",
    raise_on_error=False,
)

for violation in violations:
    print(violation.path, violation.message)
```

The same boundary is used by:

```bash
akilan validate artifacts/document
```

## Operational rationale

A cache marker, manifest, or page file must never be trusted independently after an artifact directory has moved through copying, archival storage, notebook experimentation, or pipeline stages. Validate the complete directory before cache reuse or downstream consumption.

This enhancement is additive. It does not modify the canonical artifact schema or introduce a runtime dependency.
