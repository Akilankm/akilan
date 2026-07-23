# Batch artifact directory intake CLI

`akilan-artifact-directory-intake-batch` is a fail-closed operational gate for an exact, caller-identified set of persisted artifact directories.

It combines complete directory-byte integrity, canonical `document.json` verification, schema-version compatibility, and structural validation for every manifest member. The complete batch is rejected when any member fails.

## Manifest

Create a JSON object whose keys are stable non-empty identifiers and whose values are artifact directory paths:

```json
{
  "invoice-001": "artifacts/invoice-001",
  "invoice-002": "artifacts/invoice-002"
}
```

Relative paths are resolved from the manifest directory, not the current working directory.

## Command

```bash
akilan-artifact-directory-intake-batch artifacts.json \
  --report artifacts/intake/directory-batch.json
```

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Every identified directory passed byte-integrity and semantic intake. |
| `1` | The manifest or at least one identified directory was rejected. |
| `2` | Command-line parsing or report configuration was invalid. |

Accepted evidence is written to standard output. Rejection evidence is written to standard error. `--report` persists the deterministic payload before the transient `report` field is added to console output.

## Evidence contract

The report contains:

- normalized manifest path;
- deterministic lexicographical identifier ordering;
- per-directory root path and complete nested intake evidence;
- accepted, rejected, and total counts;
- a canonical SHA-256 fingerprint for the exact ordered evidence set.

Because each member report includes the complete artifact-directory fingerprint, changing any regular persisted artifact file changes the batch fingerprint.

## Safety boundary

The command never:

- repairs or rewrites artifact files;
- follows symlinks accepted by the integrity boundary;
- migrates schema versions;
- accepts a valid subset as a complete batch;
- changes the canonical artifact schema.

PyMuPDF remains the only runtime dependency.
