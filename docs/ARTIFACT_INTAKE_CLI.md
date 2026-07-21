# Artifact intake CLI

`akilan-artifact-intake` is the installed fail-closed boundary for systems that are about to consume an AKILAN artifact.

```bash
akilan-artifact-intake artifacts/document \
  --report artifacts/intake/document.json
```

The positional source may be either an artifact directory containing `document.json` or the canonical JSON file itself.

## Decision contract

The command returns:

- `0` only when the artifact schema version is strictly compatible and the complete canonical structure is valid;
- `1` when the source is missing, unreadable, invalid JSON, not a JSON object, schema-incompatible, or structurally invalid;
- `2` for invalid command-line configuration.

Accepted evidence is written to stdout. Rejection evidence is written to stderr. `--report` persists the same deterministic decision evidence for automation and audit use.

## Example rejection evidence

```json
{
  "accepted": false,
  "compatibility": {
    "compatible": false,
    "status": "unsupported_major"
  },
  "source_path": "/workspace/artifacts/document/document.json",
  "status": "rejected",
  "violation_count": 0,
  "violations": []
}
```

Source-level failures use stable statuses:

- `missing`
- `not_a_file`
- `unreadable`
- `invalid_json`
- `invalid_root`

## Safety properties

- PyMuPDF remains the only runtime dependency.
- The source artifact is opened read-only and is never mutated.
- No migration, repair, schema inference, or compatibility override is performed.
- Strict schema compatibility and structural validation cannot be accidentally separated.
- Parsing failures use sanitized stable messages rather than raw exception details.
- This is an additive operational gate and does not change the canonical artifact schema.
