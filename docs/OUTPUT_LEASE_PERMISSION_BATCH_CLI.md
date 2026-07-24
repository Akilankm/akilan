# Batch output lease permission CLI

`akilan-output-lease-permissions-batch` audits the lease-permission boundary for an exact manifest-defined output set without mutating any destination.

## Manifest

The input is a JSON object mapping stable identifiers to artifact output destinations:

```json
{
  "invoice-001": "../artifacts/invoice-001",
  "invoice-002": "../artifacts/invoice-002"
}
```

Relative destinations are resolved from the manifest directory, not the current working directory. Identifiers and resolved destinations must be unique.

## Usage

```bash
akilan-output-lease-permissions-batch destinations.json
```

Observability mode emits deterministic JSON. It reports insecure or unsupported permission evidence without returning a policy failure, but malformed structural lease evidence and invalid destination manifests always fail closed.

For deployment or worker admission:

```bash
akilan-output-lease-permissions-batch destinations.json \
  --require-secure \
  --report artifacts/output-lease-permissions.json
```

`--require-secure` accepts the output set only when every lease is absent or has verified secure POSIX mode bits. Any group/world-writable lease directory or `owner.json`, unreadable metadata, unsupported permission semantics, malformed lease evidence, or invalid destination set rejects the complete batch.

## Exit codes

- `0`: the requested policy accepted the exact destination set.
- `1`: the destination set or lease evidence was rejected.
- `2`: command-line configuration or report persistence failed.

## Safety boundary

The command is read-only. It never acquires or releases leases, changes permissions, deletes evidence, repairs malformed locks, or infers that a lease is stale. Permission evidence can change after inspection, so admission control must still acquire the existing output-build leases before publication.

PyMuPDF remains the only runtime dependency.
