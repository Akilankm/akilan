# Batch output lease permission audit

`inspect_output_lease_permission_batch()` provides a deterministic, read-only permission audit for an exact set of artifact output destinations.

```python
from akilan.output_lease_security_batch import (
    inspect_output_lease_permission_batch,
)

report = inspect_output_lease_permission_batch(
    {
        "invoice-001": "artifacts/invoice-001",
        "invoice-002": "artifacts/invoice-002",
    }
)

if not report.secure:
    raise RuntimeError(report.to_dict())
```

## Contract

The audit:

- requires a non-empty mapping with non-empty string identifiers;
- resolves and rejects duplicate physical destinations;
- evaluates destinations in deterministic identifier order;
- preserves complete per-destination structural and permission evidence;
- treats absent leases as secure because no lease boundary exists to protect;
- fails the complete set closed when any lease is malformed, unreadable, insecure, or cannot be audited with POSIX semantics;
- never acquires, releases, repairs, deletes, or changes permissions.

## Stable batch statuses

- `secure`: every destination has acceptable evidence;
- `insecure`: at least one destination failed its permission audit;
- `invalid_destination_set`: the requested set is empty, has invalid identifiers, or resolves multiple identifiers to one destination.

`insecure_count` reports the number of destination inspections whose individual `secure` property is false. `entries` always retain the individual evidence needed to identify the exact failed boundary.

## Safety boundary

This API is an observation and policy boundary, not a reservation. A secure report does not prevent another process from creating or changing a lease after inspection. Callers that require ownership must still acquire `OutputBuildLease` or `OutputBuildLeaseBatch` immediately before protected publication.

PyMuPDF remains the only runtime dependency.
