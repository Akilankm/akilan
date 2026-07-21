# Schema version compatibility gate

AKILAN exposes a dependency-free schema-version gate for downstream systems that need to classify an artifact before full structural validation.

```python
from akilan import assess_schema_compatibility

report = assess_schema_compatibility(artifact["schema_version"])
if not report.compatible:
    raise RuntimeError(report.to_dict())
```

## Contract

Artifact schema versions use strict `major.minor.patch` notation. The parser rejects missing components, prefixes, suffixes, surrounding whitespace, non-ASCII digits, negative values, booleans, and non-string inputs.

The compatibility outcome is one of:

- `compatible`: the major version is supported;
- `invalid`: the version evidence is malformed;
- `unsupported_major`: the version is well formed but requires a different consumer or an explicitly approved migration path.

Minor and patch versions are accepted within the supported major under the additive compatibility policy. Compatibility does **not** prove that an artifact is structurally valid. Call `validate_artifact()` or `akilan validate` after this gate.

## Non-goals

This boundary does not:

- mutate an artifact;
- infer or repair a malformed version;
- migrate between major versions;
- authorize a breaking schema change;
- replace persisted-artifact validation.

A major-version migration remains blocked until its mapping, evidence preservation rules, fixtures, and owner approval are explicitly recorded.

## Evidence

`SchemaCompatibilityReport.to_dict()` produces deterministic machine-readable evidence:

```json
{
  "raw_version": "1.4.2",
  "parsed_version": "1.4.2",
  "supported_major": 1,
  "status": "compatible",
  "compatible": true,
  "message": "schema major is supported; run structural validation before consumption"
}
```

No runtime dependency is added; the implementation uses only the Python standard library.
