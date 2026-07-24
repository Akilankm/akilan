# Corpus manifest read limit

AKILAN treats the public PDF corpus manifest as control-plane input. A malformed or unexpectedly large manifest must not be loaded without a deterministic memory bound.

## Contract

`load_corpus_sources()` reads at most **1 MiB plus one sentinel byte** from the manifest before UTF-8 decoding or JSON parsing.

- A manifest of at most 1 MiB continues through the existing strict version, field, HTTPS, filename, uniqueness, and checksum validation.
- A manifest larger than 1 MiB is rejected with `CorpusSourceError` before decoding and parsing.
- Invalid UTF-8 and invalid JSON remain fail-closed `CorpusSourceError` results.
- The manifest is read-only input. Rejection never truncates, repairs, rewrites, or deletes it.

The sentinel byte distinguishes an exactly-at-limit manifest from an oversized manifest without a separate `stat()` call, avoiding a size-check/read race.

## Operational guidance

Corpus manifests should remain compact declarations of source identity, provenance, expected checksum, and test purpose. Large annotations or extracted document content belong in separate evidence artifacts rather than the control manifest.

This limit does not change the PDF download limit configured through `akilan-corpus sync --max-bytes`. The manifest bound and per-PDF download bound protect different inputs.
