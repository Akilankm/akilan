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

Owner evidence is first written to a token-specific staging file, flushed, and synchronized with `fsync()` before atomic promotion to `owner.json`. On POSIX filesystems, AKILAN then synchronizes the lease directory so the promoted directory entry crosses the same durability boundary. If writing, file synchronization, promotion, or directory synchronization fails, acquisition rolls back the owner evidence and lease directory before returning control. Platforms without POSIX directory descriptors retain atomic promotion but skip the directory `fsync()` step. A lease is never reported as acquired unless every durability operation supported by the platform succeeds.

The complete owner evidence object is checked again during release. AKILAN refuses to remove a lease when any protected field—including token, process ID, hostname, acquisition time, or destination—changed while the build was running.

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
