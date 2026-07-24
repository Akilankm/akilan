# Output lease permission audit CLI

Use the installed command to produce deterministic, read-only permission evidence for one artifact output destination:

```bash
akilan-output-lease-permissions artifacts/document
```

For deployment or job preflight, require the lease to be absent or verified secure:

```bash
akilan-output-lease-permissions artifacts/document \
  --require-secure \
  --report artifacts/output-lease-permissions.json
```

## Exit codes

- `0`: the audit satisfies the requested policy.
- `1`: structural lease evidence is invalid, or `--require-secure` rejects the audit.
- `2`: command-line configuration or report persistence failed.

Without `--require-secure`, the command is an observability boundary: secure, insecure, absent, unsupported, and unreadable permission states are emitted without modifying the lease. Invalid structural evidence still fails closed.

With `--require-secure`, only `absent` and `secure` are accepted. Insecure permissions, unsupported POSIX semantics, unreadable metadata, and invalid structural evidence return exit code `1`.

## Safety boundary

The command never:

- acquires or releases a lease;
- changes file or directory permissions;
- repairs owner evidence;
- removes a stale or malformed lease;
- declares a lease stale from process identifiers or timestamps.

On POSIX systems, group- or world-writable permissions are rejected for both the lease directory and `owner.json`. On platforms where POSIX mode-bit semantics are unavailable, `--require-secure` fails closed rather than guessing at ACL behavior.
