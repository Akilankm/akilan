# Output lease permission audit

AKILAN provides a read-only permission audit for artifact output leases:

```python
from akilan.output_lease_security import inspect_output_build_lease_permissions

inspection = inspect_output_build_lease_permissions("artifacts/document")
if not inspection.secure:
    raise RuntimeError(inspection.to_dict())
```

## Purpose

Structural lease validation proves that the lease directory and `owner.json` have the expected shape and owner identity. It does not, by itself, prove that another local account cannot rewrite that evidence.

On POSIX systems, the permission audit therefore rejects group- or world-writable access on:

- the lease directory;
- canonical `owner.json` evidence.

Read permissions are not restricted by this API because owner evidence is diagnostic rather than secret. Deployment policy may impose stricter confidentiality requirements independently.

## Stable statuses

| Status | Meaning |
|---|---|
| `absent` | No lease exists. |
| `secure` | Structural evidence is valid and neither protected path is group/world writable. |
| `insecure_permissions` | Valid lease evidence exists, but one or both paths are group/world writable. |
| `invalid_lease_evidence` | Structural lease validation failed before permission interpretation. |
| `unreadable_permissions` | Permission metadata could not be read. |
| `unsupported` | The platform does not expose POSIX mode semantics through this boundary. |

The serialized report includes four-digit octal `lease_mode` and `owner_mode` values when available, plus deterministic violation identifiers.

## Safety boundary

The audit is strictly read-only. It never:

- changes permissions;
- acquires or releases a lease;
- repairs malformed evidence;
- removes an apparently stale lease;
- infers whether a process is alive.

Operators must correct unsafe filesystem policy outside AKILAN and only remove abandoned lease evidence after independently confirming that no writer is active.

This API is additive, introduces no runtime dependency, and does not alter the canonical artifact schema.
