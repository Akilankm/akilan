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
- `valid`: a regular lease directory contains structurally valid owner evidence for the requested destination.
- `invalid_lease_path`: the expected lease path is not a regular directory or is a symlink.
- `invalid_owner_evidence`: `owner.json` is unreadable, malformed, has an invalid field, or names another destination.

Owner validation covers the UUID token, positive process identifier, non-empty hostname, UTC acquisition timestamp, and exact resolved destination. Violations are deterministic and machine-readable.

## Recovery policy

Inspection is intentionally not recovery. A lease must not be removed merely because its process identifier is absent locally or its timestamp is old: the writer may run on another host or inside another process namespace. Operators must independently establish that no writer can still publish to the destination before performing manual recovery.
