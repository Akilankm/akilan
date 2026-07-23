# Persisted artifact directory integrity

`validate_artifact_directory()` verifies that an AKILAN artifact remains complete and safe after it has been copied, cached, archived, or restored.

## Usage

```python
from akilan import validate_artifact_directory

validate_artifact_directory("artifacts/document")
```

By default, all detected violations are raised together as `ArtifactSchemaError`. For CI reports or intake workflows, request the complete list directly:

```python
violations = validate_artifact_directory(
    "artifacts/document",
    raise_on_error=False,
)
for violation in violations:
    print(violation.path, violation.message)
```

## Checks

The validator is read-only and dependency-free beyond AKILAN's existing PyMuPDF runtime dependency. It verifies:

- the artifact root and `manifest.json` exist;
- the manifest satisfies the canonical manifest contract;
- every manifest-declared path is a safe relative POSIX path;
- path traversal, absolute paths, and backslash-based paths are rejected;
- every declared page, projection, image, and render file exists;
- `document.json` parses and satisfies the canonical artifact contract;
- every declared page JSON file parses to an object;
- all failures are aggregated with actionable JSON-style paths.

## Operational role

Run this check before accepting a restored cache entry, publishing benchmark evidence, or handing artifacts to a downstream system. A cache marker or successful prior extraction is not sufficient evidence that all persisted files are still present.

The function never repairs, deletes, or rewrites artifact content. Rebuild the artifact through `PDFArtifactBuilder` when validation fails.

## Compatibility

This is an additive integrity layer. It does not modify the canonical artifact schema, stable IDs, output paths, or builder behavior.
