# Relationship inference in artifact builds

AKILAN's document relationship pass is part of the production artifact build, not a notebook-only or test-only utility.

## Build order

For every selected page, the builder now performs these document-level stages before persistence:

1. extract page-native evidence;
2. assign page-local semantics and reading order;
3. mark repeated headers and footers across pages;
4. infer cross-page sections and caption relationships;
5. calculate structural page metrics while preserving relationship evidence;
6. persist page JSON, projections, the canonical document, and the manifest.

This ordering matters. Relationship inference needs stable page-local roles and repeated-margin suppression, while page persistence must retain the additive audit evidence produced by the relationship pass.

## Persistence contract

The relationship pass owns these additive page metrics:

- `relationship_evidence`
- `relationship_ambiguities`

The standard page-metric calculation must not overwrite them. `_write_pages` therefore merges calculated structural metrics with existing inference diagnostics, with existing document-level diagnostics taking precedence on key collisions.

Every inferred edge remains deterministic and includes a stable rule identifier and bounded confidence. Ambiguous caption candidates remain unlinked and are persisted as diagnostics.

## Compatibility

This integration does not change the canonical artifact schema. It activates already-supported additive metrics and existing element relationship fields during normal `PDFArtifactBuilder` and `akilan extract` execution.

PyMuPDF remains the only runtime dependency.
