# Artifact directory intake CLI

Use the installed command when a downstream workflow must reject a persisted artifact unless the complete directory is byte-stable and its canonical `document.json` is schema-compatible and structurally valid.

```bash
akilan-artifact-directory-intake artifacts/document \
  --report artifacts/intake/document.json
```

The command performs the same fail-closed sequence as `assess_artifact_directory_intake()`:

1. inventory every regular file without following symlinks;
2. reject incomplete, unreadable, unsupported, or concurrently changing directories;
3. verify that `document.json` still matches the accepted inventory;
4. decode the verified bytes as UTF-8 JSON;
5. require an object root;
6. assess schema-version compatibility and structural validity.

## Output contract

- accepted evidence is written to stdout;
- rejected evidence is written to stderr;
- `--report` optionally persists the same deterministic JSON payload;
- exit code `0` means the complete artifact is accepted;
- exit code `1` means integrity, JSON, compatibility, or structural intake was rejected;
- exit code `2` means command-line configuration or report persistence failed.

Stable top-level statuses are:

- `accepted`
- `integrity_rejected`
- `changed_after_integrity`
- `invalid_document_json`
- `invalid_document_root`
- `artifact_rejected`

The command is read-only. It does not repair files, migrate schemas, follow symlinks, rewrite projections, or modify the canonical artifact schema.
