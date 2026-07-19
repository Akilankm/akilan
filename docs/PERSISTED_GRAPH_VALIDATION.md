# Persisted graph semantic validation

AKILAN's directory and JSON-schema validators establish that an artifact is complete, path-safe, structurally valid, and internally consistent across persisted files. Structural validity alone cannot prove that document-wide graph identities are unambiguous or that relationship targets resolve.

Use the read-only semantic boundary after loading a persisted artifact:

```python
from akilan import load_artifact_directory, find_persisted_graph_violations

artifact = load_artifact_directory("artifacts/document")
violations = find_persisted_graph_violations(artifact)

if violations:
    raise RuntimeError([violation.to_dict() for violation in violations])
```

## Enforced invariants

The validator covers all addressable element collections:

- text blocks;
- tables;
- images;
- vector drawings;
- links;
- annotations;
- widgets.

It reports:

- blank element identifiers;
- element identifiers defined more than once anywhere in the document;
- blank relationship names;
- blank relationship targets;
- self-referential edges;
- repeated targets within one relationship;
- relationship targets that do not exist in the document.

Valid cross-page and cross-collection targets are accepted because relationship IDs are document-scoped.

## Evidence contract

Every result contains a deterministic JSON-style path, message, and stable rule identifier:

- `document-element-id-uniqueness-v1`
- `relationship-target-integrity-v1`

Results are sorted and the source mapping is never mutated. This API is additive and does not change the canonical artifact schema.

## Validation order

For persisted artifacts, apply validation in this order:

1. `validate_artifact_directory()` or `load_artifact_directory()` for directory, schema, and cross-file consistency;
2. `find_persisted_graph_violations()` for semantic identity and relationship integrity;
3. domain-specific quality or benchmark acceptance gates.
