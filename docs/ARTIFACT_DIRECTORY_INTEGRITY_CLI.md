# Artifact directory integrity CLI

Use the installed integrity gate to bind handoff or audit evidence to every regular file in a persisted AKILAN artifact directory.

```bash
akilan-artifact-integrity artifacts/document \
  --report artifacts/integrity/document.json
```

The command requires a regular `document.json`, rejects symlinks and unsupported filesystem entries, and hashes every regular file without following links. Evidence contains deterministic relative POSIX paths, per-file SHA-256 digests and byte sizes, aggregate counts, and one canonical directory fingerprint.

## Exit codes

- `0`: complete directory inventory accepted
- `1`: missing, invalid, unreadable, symlinked, or otherwise unsupported artifact directory
- `2`: invalid command configuration, including an unwritable report destination

Accepted evidence is written to standard output. Rejection evidence is written to standard error. `--report` persists the same deterministic JSON payload for CI retention or downstream handoff.

## Integrity scope

This gate binds evidence to exact persisted bytes. It does not validate artifact semantics, infer compatibility, repair files, migrate schemas, or modify the artifact. Pair it with `akilan-artifact-intake` when both structural acceptance and complete-directory byte identity are required.
