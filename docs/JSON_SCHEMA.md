# Machine-readable artifact schema

AKILAN packages a JSON Schema Draft 2020-12 description of the stable document-artifact contract at:

```text
src/akilan/schemas/document-artifact-v1.schema.json
```

Downstream systems can load the schema without network access:

```python
from akilan import load_artifact_json_schema

schema = load_artifact_json_schema()
print(schema["$id"])
```

AKILAN does not add a JSON Schema engine as a runtime dependency. Use the built-in dependency-free validator for artifact intake and CI gates:

```python
from akilan import validate_artifact

validate_artifact(document_artifact)
```

## Compatibility rules

- The schema major version is independent of the package version.
- Version `1.x` permits additive fields so inference modules can publish new evidence without invalidating existing consumers.
- Required fields cannot be removed or retyped within schema major version 1.
- Unknown fields must be preserved by consumers that round-trip artifacts.
- A breaking contract requires a new schema major version and explicit owner approval.
- The checked-in JSON Schema describes structural interoperability; `validate_artifact()` additionally enforces actionable semantic checks such as canonical bounding-box ordering and unique reading-order positions.

## Reference integrity

`validate_artifact()` verifies the page-local graph in addition to field shapes:

- IDs for text blocks, tables, images, and drawings must be non-empty and unique within the page;
- every reading-order entry must reference an element present on the same page;
- the declared reading-order element type must match the referenced collection;
- malformed element entries are reported with exact JSON-style paths;
- all violations are collected in one pass so persisted artifacts can be repaired deterministically.

These checks protect downstream projections and retrieval systems from dangling or type-confused references without changing the canonical schema or requiring another runtime package.

## Distribution guarantee

The schema is stored inside the `akilan.schemas` package and is included in built wheels. `load_artifact_json_schema()` returns a newly decoded object on every call, so callers may modify their local copy without mutating process-global state.

## Updating the schema

For an additive change:

1. update the JSON Schema;
2. update the dependency-free validator when semantic validation is required;
3. add focused tests proving schema and validator parity;
4. document the new optional field;
5. run Ruff, the complete test suite, and package build validation.

Do not introduce a new schema major version without explicit approval.
