# Schema compatibility CLI

`akilan-schema-compatibility` is a dependency-free, read-only intake gate for artifact schema versions.

It classifies version compatibility before full structural validation. It does not open, migrate, repair, or rewrite an artifact.

## Usage

```bash
akilan-schema-compatibility 1.4.2
```

Persist deterministic evidence when a pipeline needs an auditable decision:

```bash
akilan-schema-compatibility 1.4.2 \
  --report artifacts/schema-compatibility.json
```

Use `--supported-major` only when testing an explicitly configured consumer policy:

```bash
akilan-schema-compatibility 2.0.0 --supported-major 2
```

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | The schema major is supported. Structural validation is still required. |
| `1` | The version is malformed or its major is unsupported. |
| `2` | The command configuration is invalid. |

## Output contract

Successful evidence is written to standard output. Rejection evidence is written to standard error. Optional persisted evidence contains:

- the raw version;
- the strict parsed version when parsing succeeds;
- the configured supported major;
- a stable status: `compatible`, `invalid`, or `unsupported_major`;
- the compatibility decision and an actionable message.

The command accepts only strict ASCII `major.minor.patch` values. Prefixes, suffixes, missing components, negative components, surrounding whitespace, and non-ASCII digits are rejected.

## Safety boundary

Compatibility is not structural validity. After a compatible result, run:

```bash
akilan validate path/to/artifact
```

No migration path is inferred or executed. Breaking schema changes and migration policy remain blocked pending explicit owner approval.
