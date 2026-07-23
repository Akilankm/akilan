# Batch output lease preflight CLI

`akilan-output-lease-batch` gives schedulers and CI one fail-closed, read-only decision over an exact manifest-defined set of artifact output destinations.

```bash
akilan-output-lease-batch destinations.json \
  --report artifacts/output-lease-preflight.json
```

The manifest must be a JSON object mapping non-empty identifiers to output paths:

```json
{
  "invoice-001": "artifacts/invoice-001",
  "invoice-002": "artifacts/invoice-002"
}
```

Relative paths are resolved from the manifest directory. Entries are evaluated and emitted in deterministic identifier order.

## Exit contract

- `0`: every destination lease is absent and the exact destination set is ready.
- `1`: the set is blocked, malformed, empty, duplicated after path resolution, or otherwise unsafe.
- `2`: command-line parsing or report persistence failed.

Accepted evidence is written to standard output. Blocking evidence is written to standard error. `--report` persists the same deterministic payload without the transient `report` field printed by the command.

## Fail-closed conditions

The command rejects the complete set when any destination has:

- an active valid lease;
- malformed owner evidence;
- an invalid or symlinked lease path;
- another lease-contract violation.

It also rejects malformed manifests, non-object JSON roots, empty identifiers or paths, empty destination sets, and multiple identifiers resolving to the same destination.

## Safety boundary

The command never:

- acquires or releases a lease;
- repairs or removes lease evidence;
- declares a lease stale;
- starts an artifact build;
- reserves a destination after preflight.

Preflight is a scheduling check, not a reservation. Each builder must still acquire `OutputBuildLease` immediately before writing because another process can acquire a lease after preflight completes.
