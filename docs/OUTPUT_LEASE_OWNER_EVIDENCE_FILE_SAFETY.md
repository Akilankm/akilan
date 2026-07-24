# Output lease owner evidence file safety

AKILAN treats `.owner.json` evidence as untrusted filesystem input. Structural path checks alone are insufficient because a path can be replaced between inspection and read.

## Read boundary

Owner evidence is opened through a file descriptor rather than `Path.read_text()` or an unbounded stream read.

Where the platform exposes the relevant flags, AKILAN uses:

- `O_NOFOLLOW` to reject symbolic-link traversal at open time;
- `O_NONBLOCK` to prevent a substituted FIFO or device from blocking inspection;
- `O_BINARY` where required for byte-stable reads.

After opening, `fstat()` must identify a regular file. The descriptor is then read through the existing 16 KiB limit plus one overflow sentinel before UTF-8 decoding and JSON parsing.

## Failure behavior

Any open, type, size, decoding, or parsing failure produces the existing fail-closed `invalid_owner_evidence` result. AKILAN does not:

- follow a symbolic link to external owner evidence;
- wait for FIFO input;
- truncate or rewrite invalid evidence;
- infer that an unreadable lease is abandoned;
- remove the lease automatically.

A competing writer still receives `OutputLeaseError` while the lease directory exists.

## Platform boundary

`O_NOFOLLOW` is used when supplied by the operating system. On platforms without it, the existing directory-entry validation and post-open regular-file verification remain active, but operators should treat filesystem-level replacement resistance as platform dependent.

## Recovery

Operators must independently establish that no writer is active before manually recovering invalid lease evidence. Preserve the lease directory for diagnosis whenever ownership cannot be proven.
