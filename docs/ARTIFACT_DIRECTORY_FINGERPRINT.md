# Artifact directory fingerprint

`assess_artifact_directory_integrity()` produces deterministic, read-only byte identity for a complete persisted artifact directory.

```python
from akilan import assess_artifact_directory_integrity

report = assess_artifact_directory_integrity("artifacts/document")
if not report.accepted:
    raise RuntimeError(report.to_dict())
```

## Evidence contract

The report contains the normalized artifact root, one lexicographically ordered entry for every regular file, each file's relative POSIX path, SHA-256 digest and byte size, aggregate counts, and a canonical SHA-256 fingerprint over the complete ordered inventory.

Changing any canonical JSON, projection, extracted asset, render, or other regular file changes the directory fingerprint.

## Stable file reads

Each file is opened through a descriptor without following symlinks where the platform supports `O_NOFOLLOW`. The implementation compares path and descriptor metadata before reading, reads from the descriptor in bounded chunks, and compares descriptor and path metadata again after reading.

The complete directory is rejected with `changed_during_read` when the file identity, size, or nanosecond modification time changes during evidence generation. This prevents a check-to-open symlink swap or concurrent writer from producing evidence assembled from an unstable directory snapshot.

## Fail-closed behavior

The complete directory is rejected when the root is missing or not a directory, `document.json` is missing or invalid as a file, a symlink is present, an unsupported filesystem entry is encountered, a file changes while being read, or any file cannot be read completely. Rejected reports contain no partial inventory.

Symlinks are never followed. This prevents a persisted artifact from extending its integrity boundary to mutable files outside the artifact root.

## Relationship to structural validation

`validate_artifact_directory()` verifies declared paths and persisted artifact structure. The fingerprint API complements that boundary by binding downstream evidence to the exact bytes of every regular file, including projections and assets that can change without altering `document.json`.

Use structural validation for correctness and the fingerprint report for immutable handoff, caching, archival, and audit evidence.

## Compatibility

This API is additive and does not modify the canonical artifact schema. It uses only the Python standard library; PyMuPDF remains AKILAN's sole runtime dependency.
