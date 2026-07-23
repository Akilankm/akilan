# Batch output lease preflight

Enterprise orchestration commonly schedules several PDF artifact builds as one logical batch. Checking each destination independently can allow a valid subset to start before a later destination is discovered to be leased or malformed.

`assess_output_lease_batch_preflight()` provides one deterministic, read-only decision over the exact caller-identified destination set.

```python
from akilan.output_lease_batch import assess_output_lease_batch_preflight

report = assess_output_lease_batch_preflight(
    {
        "invoice-001": "artifacts/invoice-001",
        "invoice-002": "artifacts/invoice-002",
    }
)

if not report.ready:
    raise RuntimeError(report.to_dict())
```

## Decision states

- `ready`: every requested destination has no lease path.
- `blocked`: at least one destination has an active valid lease or malformed lease evidence.
- `invalid_destination_set`: the set is empty, contains an invalid identifier, or maps multiple identifiers to the same resolved destination.

A batch is ready only when **every** inspection reports `absent`. A valid active lease is intentionally blocking. Invalid lease evidence is also blocking because automation cannot safely infer whether another writer is active.

## Determinism and audit evidence

Entries are emitted in identifier order, independent of mapping insertion order. Each entry preserves the complete single-destination inspection evidence:

- resolved destination;
- lease path;
- status and presence;
- validated owner evidence when available;
- contract violations.

Duplicate resolved destinations are rejected so one physical output cannot be represented as two independent batch members.

## Safety boundary

The preflight never:

- creates or acquires a lease;
- releases or removes a lease;
- edits owner evidence;
- guesses whether a lease is stale;
- starts any artifact build.

The result is a scheduling precondition, not a reservation. Individual builders must still acquire `OutputBuildLease` immediately before work begins because another process may acquire a lease after preflight.
