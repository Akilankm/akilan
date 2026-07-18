# Atomic artifact publication

AKILAN builds every artifact in a uniquely named sibling staging directory and publishes it only after extraction and serialization finish successfully.

## Guarantees

- A failed extraction does not delete or partially overwrite the last known-good artifact.
- `overwrite=False` still rejects a non-empty destination before extraction starts.
- `overwrite=True` replaces the previous artifact only after the new artifact is complete.
- Temporary staging and backup directories are removed after successful publication or extraction failure.
- The canonical artifact schema and generated relative paths are unchanged.

## Publication sequence

1. Validate the source path and destination overwrite policy.
2. Create a private sibling staging directory.
3. Extract and serialize the complete artifact into staging.
4. Move an existing destination to a temporary backup.
5. Atomically rename staging to the requested destination on the same filesystem.
6. Remove the backup after publication succeeds.
7. Restore the backup if publication fails after the old destination was moved.

The destination and its staging directory intentionally share a parent directory so the final rename remains a same-filesystem operation.

## Operational behavior

Callers should treat the presence of the requested destination as evidence of the most recently completed publication. Benchmark failures may still report partial extraction diagnostics separately, but incomplete builder output is never exposed under the final destination path.
