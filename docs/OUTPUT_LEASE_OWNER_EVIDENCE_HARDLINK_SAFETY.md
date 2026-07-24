# Output lease owner evidence hard-link safety

AKILAN treats `.destination.akilan.lock/owner.json` as lease-local ownership evidence. A regular file can still be unsafe when it has multiple hard links because another pathname can mutate the same inode outside the lease directory.

## Contract

On POSIX filesystems, valid owner evidence must satisfy all of the following:

- the lease directory contains exactly one entry named `owner.json`;
- `owner.json` is a regular file and not a symbolic link;
- the opened file descriptor reports exactly one hard link;
- the payload is at most 16 KiB, UTF-8 JSON, and matches the exact owner schema.

A hard-linked `owner.json` is reported as:

```text
status: invalid_owner_evidence
violation: owner_json_must_have_single_link
```

The descriptor-level link-count check is repeated after opening the file. This closes the gap between path inspection and bounded evidence reading: a path that is replaced with a hard link during inspection is still rejected before parsing.

## Fail-closed behavior

AKILAN does not unlink, repair, rewrite, or recover hard-linked evidence automatically. In particular:

- read-only inspection leaves both paths and the shared inode unchanged;
- competing acquisition remains blocked by the existing lease directory;
- release refuses to remove the lease because exclusive ownership cannot be proven;
- operators must investigate ownership independently before any manual recovery.

## Dependency and schema impact

This hardening uses Python standard-library filesystem metadata only. PyMuPDF remains the sole runtime dependency, and the artifact schema is unchanged.
