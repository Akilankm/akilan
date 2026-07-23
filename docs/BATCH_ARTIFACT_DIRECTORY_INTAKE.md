# Batch artifact directory intake

AKILAN can assess an exact caller-identified set of persisted artifact directories before a downstream system consumes any member.

```python
from akilan import assess_artifact_directory_batch_intake

report = assess_artifact_directory_batch_intake(
    {
        "invoice-001": "artifacts/invoice-001",
        "invoice-002": "artifacts/invoice-002",
    }
)

if not report.accepted:
    raise RuntimeError(report.to_dict())
```

## Contract

The batch gate delegates each member to `assess_artifact_directory_intake()`. A member is accepted only when:

1. every persisted regular file is inventoried and fingerprinted;
2. no symlink, unsupported entry, unreadable file, or concurrent mutation is detected;
3. `document.json` still matches the accepted byte inventory;
4. the verified bytes decode as a JSON object;
5. the artifact schema version is compatible;
6. the canonical artifact passes structural validation.

The complete batch is accepted only when it is non-empty and every identified member passes.

## Deterministic evidence

Entries are ordered by their caller-provided identifiers. The report includes:

- accepted, rejected, and total counts;
- complete per-member directory-integrity and semantic-intake evidence;
- normalized absolute artifact roots;
- a canonical SHA-256 fingerprint over the exact ordered batch evidence.

Mapping insertion order does not affect the report. Changing any persisted regular file in any member changes the batch fingerprint.

## Failure behavior

An empty set fails closed with `empty_batch`. If any member fails, the report status is `rejected`, but evidence for every member is retained so operators can repair the complete set in one cycle. A valid subset must never be treated as an accepted batch.

Identifiers must be non-empty strings. Invalid identifiers raise `ValueError` before any artifact directory is accessed.

## Boundaries

The gate is read-only. It does not:

- repair or rewrite artifacts;
- migrate artifact schemas;
- override compatibility policy;
- delete source evidence;
- publish partial replacement artifacts.

PyMuPDF remains AKILAN's only runtime dependency.
