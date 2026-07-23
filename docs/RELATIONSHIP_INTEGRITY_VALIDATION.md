# Relationship integrity validation

AKILAN relationship inference is deliberately conservative, but persisted graph edges still need a deterministic intake check before downstream systems trust them.

Use the read-only validator after extraction or when loading an artifact in an enterprise pipeline:

```python
from akilan.relationship_integrity import find_relationship_integrity_violations

violations = find_relationship_integrity_violations(document.pages)
if violations:
    raise ValueError([item.to_dict() for item in violations])
```

## Contract

The validator builds one document-scoped index across text blocks, tables, images, drawings, links, annotations, and widgets. Cross-page targets are therefore valid when the referenced element exists anywhere in the document.

It reports:

- blank relationship names;
- blank target identifiers;
- self-referential edges;
- repeated targets within one source relationship;
- dangling target identifiers.

Every result includes the source page, source element, relationship name, target identifier, reason, and stable rule identifier `relationship-target-integrity-v1`.

## Determinism and safety

Validation is independent of page, element, relationship-key, and target order. It does not mutate source artifacts, remove native PyMuPDF evidence, infer replacement targets, or change the canonical artifact schema.

This check complements schema validation: schema validation verifies artifact shape, while relationship integrity validation verifies that graph references resolve to real document elements.
