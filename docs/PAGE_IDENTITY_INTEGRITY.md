# Page identity integrity

AKILAN preserves original PDF page coordinates even when extraction selects a non-contiguous page subset. Downstream joins, cache reuse, resumable builds, citations, and rendered-page lookups therefore depend on stable document-level page identities.

Use the dependency-free integrity check after canonical schema validation:

```python
from akilan import validate_artifact, validate_page_identities

validate_artifact(document)
validate_page_identities(document)
```

## Enforced invariants

For every serialized page:

- `page_index` is the original zero-based source index;
- `page_number` is the original one-based source number;
- `page_number == page_index + 1`;
- page indexes and page numbers are unique;
- pages appear in strictly increasing source order.

Non-contiguous identities are valid. For example, `(page_index, page_number)` pairs `(1, 2)`, `(4, 5)`, and `(9, 10)` correctly represent a partial extraction of source pages 2, 5, and 10.

## Failure behavior

`validate_page_identities()` aggregates all detected violations and raises `ArtifactSchemaError` by default. Pass `raise_on_error=False` to receive a complete list of `SchemaViolation` objects with exact JSON-style paths.

The function intentionally defers object-shape and scalar-type validation to `validate_artifact()`. This separation prevents duplicate diagnostics while keeping document-level invariants independently testable.
