# Artifact validation CLI

Use `akilan validate` as a dependency-free intake gate for persisted AKILAN artifacts before cache reuse, notebook analysis, archival, or downstream processing.

```bash
akilan validate artifacts/document
```

A valid artifact writes a JSON summary to standard output and exits with code `0`:

```json
{
  "artifact": "/absolute/path/artifacts/document",
  "valid": true,
  "schema_version": "1.0.0",
  "pages": 12,
  "violation_count": 0
}
```

An invalid artifact writes a complete machine-readable violation report to standard error and exits with code `1`:

```json
{
  "artifact": "/absolute/path/artifacts/document",
  "valid": false,
  "violation_count": 2,
  "violations": [
    {
      "path": "$.artifact_files.document_markdown",
      "message": "declared artifact file does not exist: document.md"
    },
    {
      "path": "$.document_json",
      "message": "contains invalid JSON"
    }
  ]
}
```

## Validation boundary

The command delegates to `load_artifact_directory()` and therefore validates the full persisted boundary before returning success:

- manifest structure;
- safe relative artifact paths;
- existence of every declared file;
- JSON readability;
- canonical artifact structure and reference integrity;
- source-stable page identities.

The command is read-only. It never repairs, downloads, deletes, or rewrites artifact content.

## CI usage

```bash
akilan validate artifacts/document > validation.json
```

Because invalid artifacts return a nonzero exit status, the command can be used directly as a CI gate. Diagnostic JSON remains on standard error so standard output contains only a successful result.

## Runtime policy

The command introduces no additional runtime dependency. PyMuPDF remains AKILAN's only runtime dependency.
