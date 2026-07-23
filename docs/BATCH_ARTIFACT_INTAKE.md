# Batch artifact intake

Enterprise consumers commonly need an all-or-nothing decision for an exact set of canonical artifacts. Validating members independently is insufficient because a pipeline can accidentally consume the accepted subset and silently omit rejected inputs.

`assess_artifact_batch_intake()` composes the existing schema-compatibility and structural-validation boundaries without changing either contract.

```python
from akilan import assess_artifact_batch_intake

report = assess_artifact_batch_intake(
    {
        "invoice-001": artifact_a,
        "invoice-002": artifact_b,
    }
)

if not report.accepted:
    raise RuntimeError(report.to_dict())
```

## Contract

- The batch is accepted only when it is non-empty and every member is accepted.
- Caller-provided artifact identifiers must be non-empty strings.
- Entries are evaluated and emitted in lexicographical identifier order.
- Compatibility and structural violations remain available per member.
- A canonical SHA-256 fingerprint binds the decision to the ordered intake evidence.
- Mapping insertion order does not affect the report or fingerprint.
- Input artifacts are never mutated, repaired, migrated, or rewritten.

The fingerprint is evidence for the intake decision, not a content-addressed artifact identity. Consumers requiring file-integrity guarantees should combine this gate with artifact-directory integrity validation.

This API is additive. It does not alter the canonical artifact schema, compatibility policy, or the single-artifact `assess_artifact_intake()` behavior.
