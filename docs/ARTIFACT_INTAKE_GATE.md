# Artifact intake compatibility gate

`assess_artifact_intake()` combines schema-version compatibility assessment with structural artifact validation at one read-only consumption boundary.

```python
from akilan.artifact_intake import assess_artifact_intake

report = assess_artifact_intake(artifact)
if not report.accepted:
    raise RuntimeError(report.to_dict())
```

## Decision contract

An artifact is accepted only when both conditions hold:

1. `schema_version` is strict ASCII `major.minor.patch` and its major is supported.
2. The decoded artifact satisfies the dependency-free canonical structural validator.

The machine-readable report contains compatibility evidence, ordered structural violations, a violation count, and the final acceptance decision.

## Why this boundary exists

The structural validator historically accepted some version strings that began with the supported integer major. Compatibility policy is intentionally stricter. Calling the two APIs separately can therefore create an unsafe consumer that checks structure but forgets strict version compatibility.

The intake gate makes the safe composition explicit while preserving both existing APIs for specialized callers.

## Safety properties

- PyMuPDF remains the only runtime dependency.
- The input mapping is not mutated.
- No schema migration is inferred or executed.
- Unsupported majors fail closed.
- Malformed versions fail closed even when the remaining structure is valid.
- Structural diagnostics are still collected for actionable repair evidence.
- This is an additive consumer boundary; it does not change the canonical artifact schema.
