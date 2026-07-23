# Output lease inspection

AKILAN exposes a read-only diagnostic boundary for artifact output leases:

```python
from akilan.output_lease import inspect_output_build_lease

inspection = inspect_output_build_lease("artifacts/document")
print(inspection.to_dict())
```

The inspection never acquires, releases, repairs, deletes, or declares a lease stale. It only reports evidence for the exact resolved destination.

## Stable statuses

- `absent`: no lease path exists.
- `valid`: a regular lease directory contains exactly one regular `owner.json` file with structurally valid owner evidence for the requested destination.
- `invalid_lease_path`: the expected lease path is not a regular directory or is a symlink.
- `invalid_owner_evidence`: `owner.json` is unreadable, malformed, has missing or extra fields, names another destination, or the lease directory contains unexpected entries.

Owner validation covers the exact field set, UUID token, positive process identifier, non-empty hostname, UTC acquisition timestamp, and exact resolved destination. The lease directory must contain only a non-symlink regular `owner.json` file. Violations are deterministic and machine-readable.

Release uses the same inspection boundary before mutation. AKILAN refuses to delete a lease when any owner field changes, when the owner evidence shape changes, or when another entry appears in the lease directory. This prevents cleanup from deleting evidence that may have been replaced or supplemented by another actor.

## Recovery policy

Inspection is intentionally not recovery. A lease must not be removed merely because its process identifier is absent locally or its timestamp is old: the writer may run on another host or inside another process namespace. Operators must independently establish that no writer can still publish to the destination before performing manual recovery.
