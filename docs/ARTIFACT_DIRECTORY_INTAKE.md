# Artifact directory intake gate

Use `assess_artifact_directory_intake()` when a downstream system must consume a complete persisted artifact rather than validating `document.json` in isolation.

```python
from akilan import assess_artifact_directory_intake

report = assess_artifact_directory_intake("artifacts/document")
if not report.accepted:
    raise RuntimeError(report.to_dict())
```

The gate is fail-closed and read-only. It performs these boundaries in order:

1. fingerprint every regular file in the artifact directory without following symlinks;
2. require a complete accepted directory-integrity report;
3. read `document.json` and verify its bytes still match the accepted inventory;
4. decode the same bytes as UTF-8 JSON;
5. require an object root;
6. assess schema-version compatibility and structural validity.

A directory is accepted only when all persisted bytes are inventoried and the canonical document is compatible and structurally valid.

## Stable statuses

- `accepted`
- `integrity_rejected`
- `changed_after_integrity`
- `invalid_document_json`
- `invalid_document_root`
- `artifact_rejected`

The report preserves complete directory-integrity evidence and, when parsing succeeds, the existing artifact-intake evidence. It does not repair files, migrate schemas, follow symlinks, or modify the artifact.

This is an additive consumption boundary. It does not change the canonical artifact schema or authorize migration between schema majors.
