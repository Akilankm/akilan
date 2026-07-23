# Output lease inspection CLI

`akilan-output-lease` exposes the read-only output lease inspection boundary as an installed operational command.

```bash
akilan-output-lease artifacts/document
```

The command never acquires, releases, repairs, removes, or automatically declares a lease stale. It reports deterministic JSON describing the resolved artifact destination, lease path, presence, owner evidence, validation status, and violations.

## Operational preflight

Use `--require-absent` before starting work that must not overlap an active writer:

```bash
akilan-output-lease artifacts/document \
  --require-absent \
  --report artifacts/lease-preflight.json
```

Exit status:

- `0`: inspection evidence is valid and the requested policy is satisfied;
- `1`: lease evidence is malformed, or `--require-absent` found a valid active lease;
- `2`: invalid command usage or an unwritable report path.

Without `--require-absent`, a valid active lease is accepted as trustworthy diagnostic evidence. This mode is intended for observability. With `--require-absent`, the same valid active lease is rejected operationally.

## Stable lease states

- `absent`: no lease path exists;
- `valid`: a regular lease directory contains valid owner evidence bound to the requested destination;
- `invalid_lease_path`: the lease path is not a regular non-symlink directory;
- `invalid_owner_evidence`: `owner.json` is missing, malformed, or violates the owner contract.

Malformed lease evidence always fails closed. Operators must independently establish that no writer is active before recovering an abandoned lease; the command intentionally performs no stale-lock inference or cleanup.
