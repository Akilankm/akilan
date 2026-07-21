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

Each readable member entry includes:

- `source_path` for the exact canonical `document.json` assessed;
- `document_sha256` for the exact source bytes;
- `document_size_bytes`;
- compatibility and structural validation evidence.

The top-level canonical SHA-256 fingerprint is computed over the ordered entries, including the document byte identity. Therefore, formatting-only or content changes to an otherwise valid `document.json` produce different intake evidence. Missing or non-file members expose `null` byte identity rather than implying that content was verified.

The report also includes deterministic identifier ordering and accepted/rejected counts. A valid subset never causes the complete manifest to pass.

## Integrity scope

The byte identity binds the intake decision to the exact canonical `document.json` files consumed by this command. It does not recursively hash optional projections, extracted assets, page renders, or other files referenced by the artifact. Consumers that require complete directory integrity should additionally use AKILAN's artifact-directory validation boundary.

## Safety properties

- PyMuPDF remains the only runtime dependency.
- Artifacts and the manifest are opened read-only.
- SHA-256 is computed incrementally with bounded memory.
- No migration, repair, compatibility override, or canonical schema change occurs.
- Passwords or external services are not involved.
- Malformed source files produce stable sanitized statuses rather than tracebacks.
