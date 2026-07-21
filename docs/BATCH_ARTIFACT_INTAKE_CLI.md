# Batch artifact intake CLI

`akilan-artifact-intake-batch` provides an all-or-nothing operational gate for an exact caller-defined set of canonical artifacts.

```bash
akilan-artifact-intake-batch artifacts.json \
  --report artifacts/intake/batch.json
```

The manifest is a JSON object mapping stable, non-empty artifact identifiers to artifact directories or canonical `document.json` files:

```json
{
  "invoice-001": "artifacts/invoice-001",
  "invoice-002": "artifacts/invoice-002/document.json"
}
```

Relative paths resolve from the manifest directory, not the current working directory.

## Decision contract

The command returns:

- `0` only when the manifest is non-empty and every identified artifact is readable, schema-compatible, and structurally valid;
- `1` when the manifest or any member is missing, unreadable, malformed, incompatible, or structurally invalid;
- `2` for invalid command-line configuration.

Accepted evidence is written to stdout. Rejection evidence is written to stderr. `--report` persists deterministic JSON evidence.

The report includes deterministic identifier ordering, per-member source paths and intake evidence, accepted/rejected counts, and a canonical SHA-256 fingerprint for the exact ordered decision evidence. A valid subset never causes the complete manifest to pass.

## Safety properties

- PyMuPDF remains the only runtime dependency.
- Artifacts and the manifest are opened read-only.
- No migration, repair, compatibility override, or canonical schema change occurs.
- Passwords or external services are not involved.
- Malformed source files produce stable sanitized statuses rather than tracebacks.
- The fingerprint represents intake-decision evidence; it is not a replacement for artifact-directory integrity verification.
