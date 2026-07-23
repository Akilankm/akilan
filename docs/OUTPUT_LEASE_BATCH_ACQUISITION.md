# Batch output lease acquisition

`OutputBuildLeaseBatch` provides an all-or-nothing writer reservation for an exact set of artifact destinations.

```python
from akilan.output_lease_batch import OutputBuildLeaseBatch

with OutputBuildLeaseBatch(
    {
        "invoice-001": "artifacts/invoice-001",
        "invoice-002": "artifacts/invoice-002",
    }
):
    build_complete_batch()
```

## Contract

The batch boundary:

- validates the exact destination set before acquisition;
- rejects empty identifiers, empty sets, duplicate resolved destinations, active leases, and malformed lease evidence;
- acquires destinations in deterministic identifier order;
- uses each destination's atomic lease-directory creation as the arbitration operation;
- rolls back leases acquired by the current batch when a later acquisition loses a race or process-level interruption occurs;
- releases independently verified leases in reverse acquisition order;
- never removes, repairs, or declares foreign lease evidence stale;
- preserves changed owner evidence and fails closed when release ownership cannot be proven.

A successful read-only batch preflight is not a reservation. Use `OutputBuildLeaseBatch` around the complete build and publication operation when multiple outputs must be produced as one scheduled unit.

## Failure semantics

If a competing writer claims a later destination after construction but before acquisition completes, the batch releases every earlier lease it acquired and propagates the acquisition failure. The competing writer's lease remains untouched.

Partial acquisition is also rolled back when acquisition is interrupted by process-control exceptions such as `KeyboardInterrupt` or `SystemExit`. After safe cleanup, the original interrupt is re-raised unchanged. If rollback itself cannot prove ownership, AKILAN raises `OutputLeaseError` chained from the original interrupt and retains only the disputed evidence.

If rollback or release cannot prove ownership of one acquired lease, that lease evidence is retained for investigation. Cleanup continues for every other independently verified lease, so a disputed destination does not leave unrelated outputs locked. The operation raises `OutputLeaseError` containing every release failure after all safe cleanup attempts complete.

A later `release()` call retries only the leases whose ownership could not previously be proven. This allows an operator to restore verified owner evidence and complete cleanup without reacquiring or disturbing destinations already released successfully.

When the protected `with` block fails and lease cleanup also fails, AKILAN raises `OutputLeaseBatchContextError`. Its `body_error` and `release_error` attributes preserve both failures, and the original protected-block failure remains the exception cause. This prevents cleanup failure from silently replacing the root build or publication failure. If only cleanup fails, the existing `OutputLeaseError` behavior is unchanged.

## Operational boundary

The lease coordinates writers that use the same filesystem namespace and AKILAN lease convention. It does not provide a distributed consensus protocol, stale-owner detection, or transactional rollback of artifacts already written outside the lease-protected block.
