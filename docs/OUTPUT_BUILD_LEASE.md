# Artifact output build lease

AKILAN serializes writers targeting the same artifact directory with a dependency-free, fail-closed output lease.

## Protected boundary

`PDFArtifactBuilder.build()` acquires an exclusive sibling lease before it:

1. validates the destination and overwrite policy;
2. computes cache identity;
3. creates a staging directory;
4. extracts and serializes the artifact;
5. publishes the completed staging directory atomically.

For an output directory named `artifact`, the lease directory is:

```text
.artifact.akilan.lock/
└── owner.json
```

Directory creation is the atomic arbitration operation. A second writer targeting the same resolved destination fails before creating staging or backup state.

## Owner evidence

`owner.json` records diagnostic evidence:

- unique lowercase UUIDv4 lease token encoded as 32 hexadecimal characters;
- process ID;
- hostname;
- UTC acquisition time;
- absolute resolved destination.

Inspection validates the token structurally and semantically: hexadecimal shape alone is insufficient; the UUID version and RFC 4122 variant bits must identify a genuine UUIDv4 value. This prevents malformed or fabricated owner identities from being accepted as canonical lease evidence.

On POSIX systems, acquisition enforces exact private permissions independently of the caller's `umask`: the lease directory is set to `0700` and the token-specific owner staging file is set to `0600` before owner evidence is written. Atomic promotion preserves the staging file mode for canonical `owner.json`. Permission-hardening failure enters the same ownership-safe rollback path as publication failure, so an insecure or partially initialized lease is never reported as acquired. Platforms without POSIX mode-bit semantics retain the existing structural and durability guarantees and can be evaluated through the read-only permission-audit APIs.

Owner evidence is first written to a token-specific staging file, flushed, and synchronized with `fsync()` before atomic promotion to `owner.json`. On POSIX filesystems, AKILAN then synchronizes the lease directory so the promoted directory entry crosses the same durability boundary. If permission enforcement, writing, file synchronization, promotion, or directory synchronization fails, acquisition rolls back the owner evidence and lease directory before returning control. Platforms without POSIX directory descriptors retain atomic promotion but skip the directory `fsync()` step. A lease is never reported as acquired unless every supported security and durability operation succeeds.

The complete owner evidence object is checked again during release. AKILAN refuses to remove a lease when any protected field—including token, process ID, hostname, acquisition time, or destination—changed while the build was running.

After verified release removes `owner.json` and the lease directory, AKILAN synchronizes the lease directory's parent on POSIX systems. This makes removal durable across a process or host failure instead of relying only on the in-memory directory state. If the parent synchronization fails, the lease is already physically absent and the in-process lease state is cleared, but AKILAN raises `OutputLeaseError` because crash durability could not be confirmed. Calling `release()` again is safe and becomes a no-op.

Interrupted owner-publication rollback applies the same parent-directory synchronization after removing the incomplete lease directory. A rollback synchronization failure therefore fails closed rather than reporting a fully durable cleanup.

## Failure behavior

The lease is released when the protected build scope exits, including extraction and publication failures. Existing atomic-output guarantees remain unchanged: failed builds do not replace the last known-good artifact.

When the protected `with` block fails and lease cleanup also fails, AKILAN raises `OutputLeaseContextError`. Its `body_error` and `release_error` attributes preserve both failures, while the original protected-operation failure remains the exception cause. This prevents a cleanup failure from hiding the extraction or publication root cause. When only cleanup fails, the existing `OutputLeaseError` behavior is unchanged.

AKILAN does **not** automatically delete apparently stale leases. PID reuse, containers, network filesystems, and multiple hosts make automatic stale-owner inference unsafe. An abandoned lease must be removed only after an operator independently confirms that no writer is using the destination.

## Concurrency boundary

- Different destinations may be built concurrently.
- The same destination permits exactly one writer.
- A single `pymupdf.Document` is never shared across workers by this mechanism.
- The lease coordinates filesystem publication; it does not claim that arbitrary PyMuPDF objects are thread-safe.

This is an additive operational safeguard. It does not alter the canonical artifact schema or add a runtime dependency.
