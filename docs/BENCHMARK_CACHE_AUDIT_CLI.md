# Benchmark cache audit CLI

AKILAN exposes the corpus-level benchmark cache integrity audit as a fail-closed command-line gate:

```bash
akilan audit-benchmark-cache artifacts/benchmark \
  --report artifacts/benchmark-cache-audit.json
```

The command recursively discovers directories containing `.akilan-benchmark-cache.json` and validates each entry using the same read-only integrity contract used by benchmark cache reuse.

## Exit contract

| Exit code | Meaning |
|---:|---|
| `0` | At least one cache entry was found and every entry passed validation. |
| `1` | The root is missing, empty, not a directory, or at least one entry is invalid. |

Successful output is written to standard output. Failed audit evidence is written to standard error so shell and CI workflows can separate accepted results from blocking diagnostics.

## Report evidence

The JSON payload includes:

- stable relative artifact-directory paths;
- valid and invalid entry counts;
- complete machine-readable violation paths and messages;
- a deterministic report fingerprint;
- the persisted report path when `--report` is supplied.

The command never repairs, deletes, rebuilds, or mutates benchmark artifacts. It only evaluates whether persisted cache evidence is safe to trust.

## CI example

```bash
set -euo pipefail
akilan audit-benchmark-cache artifacts/benchmark \
  --report artifacts/benchmark-cache-audit.json
```

A missing or empty cache root fails rather than silently passing, which prevents an absent benchmark run from being misreported as valid cache coverage.
