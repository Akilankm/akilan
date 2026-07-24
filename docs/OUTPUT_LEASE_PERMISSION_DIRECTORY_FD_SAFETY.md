# Output lease permission audit directory anchoring

AKILAN treats output-lease paths as concurrently mutable filesystem input. A structural inspection followed by independent path-based permission reads can be redirected if the lease directory is renamed and replaced between those operations.

## Anchored audit boundary

On supported POSIX systems, the permission audit now:

1. opens the lease directory with `O_DIRECTORY` and `O_NOFOLLOW`;
2. opens `owner.json` relative to that directory descriptor;
3. obtains both permission records with `fstat()`;
4. closes both descriptors on every success or failure path.

The lease directory descriptor is established before the owner lookup, so both mode records are tied to one opened directory object rather than two independently resolved paths.

The `owner.json` lookup therefore remains attached to the directory that was actually opened. Replacing the visible lease path after that point cannot redirect the audit toward unrelated evidence.

## Fail-closed behavior

The audit reports `unsupported` when the platform cannot provide the descriptor-relative, no-follow semantics required for this guarantee. Open, metadata, or object-type failures report `unreadable_permissions`. AKILAN does not fall back to a weaker path-based permission claim, mutate the lease, repair evidence, or infer stale ownership.

The structural lease inspection remains the first gate. Descriptor anchoring strengthens the subsequent mode-bit evidence without changing the canonical artifact schema, lease owner schema, or runtime dependency policy.

## Operational interpretation

Permission evidence is still a point-in-time observation. A worker must acquire the existing output-build lease before publication; a secure audit result is not a substitute for arbitration.

PyMuPDF remains the sole runtime dependency.
