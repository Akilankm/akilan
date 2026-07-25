# Corpus manifest file safety

The public-corpus manifest is control-plane input. `load_corpus_sources()` therefore reads it through a bounded operating-system file descriptor rather than a path-based text stream.

## Guarantees

- The opened object must be a regular file according to `fstat()`.
- Symbolic-link traversal is rejected on platforms that expose `O_NOFOLLOW`.
- `O_NONBLOCK` is used when available so FIFO and other special-file substitutions cannot stall the process before type validation.
- At most 1 MiB plus one overflow sentinel byte is read.
- Oversized input is rejected before UTF-8 decoding or JSON parsing.
- Rejected manifests and external targets are never repaired, truncated, rewritten, or deleted.
- Existing manifest version, HTTPS, filename, uniqueness, and checksum validation remains unchanged.

## Platform boundary

The regular-file descriptor check is portable. Exact symbolic-link rejection depends on operating-system support for `O_NOFOLLOW`; callers running on platforms without it should place manifests in trusted, access-controlled directories.

## Recovery

Replace an invalid manifest with a regular UTF-8 JSON file that satisfies the documented corpus schema. The loader intentionally performs no automatic recovery because modifying control-plane evidence would hide the original failure state.
