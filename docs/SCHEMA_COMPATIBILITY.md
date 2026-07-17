# Artifact Schema Compatibility

AKILAN's canonical JSON artifact is a downstream integration contract. Package versions and artifact-schema versions evolve independently.

## Version policy

- `schema_version` uses semantic versioning.
- A major version change may remove, rename, reinterpret, or change the type of an existing field.
- A minor version change may add optional fields or additive enum values.
- A patch version may clarify validation or serialization without changing valid artifact meaning.
- Consumers must reject unsupported major versions rather than guessing.

The current validator accepts schema major version `1`.

## Validation API

```python
import json
from pathlib import Path

from akilan import ArtifactSchemaError, validate_artifact

artifact = json.loads(Path("artifact/document.json").read_text(encoding="utf-8"))

try:
    validate_artifact(artifact)
except ArtifactSchemaError as exc:
    for violation in exc.violations:
        print(violation.path, violation.message)
```

For reporting workflows that must not raise:

```python
violations = validate_artifact(artifact, raise_on_error=False)
```

Each violation carries a JSON-style path such as `$.pages[2].cropbox`, enabling CI, notebooks, and enterprise ingestion systems to report exact repair locations.

## Validation scope

The dependency-free validator checks the stable contract boundary:

- required document-level collections and mappings;
- supported schema major version;
- page identity, dimensions, rotation, geometry, and element collections;
- valid bounding-box shape and coordinate ordering;
- reading-order type, identifier, geometry, and duplicate-order constraints.

It intentionally does not over-constrain implementation-owned metadata dictionaries. This permits additive metadata while protecting structural invariants.

## Compatibility guarantees

- Existing source evidence is not deleted during additive schema evolution.
- Stable element identifiers are opaque strings; consumers must not parse meaning from their format.
- Unknown optional fields must be preserved by lossless intermediaries.
- A malformed artifact must fail with actionable paths; it must never be silently treated as complete.
- Breaking schema changes require an explicit migration path and owner approval.

## CI use

Tests should validate generated artifacts after extraction and before publishing benchmark or notebook results. Persisted artifacts received from another system should be validated before projections or analytics are computed.
