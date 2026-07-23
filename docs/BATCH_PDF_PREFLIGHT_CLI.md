# Batch PDF preflight CLI

Use `akilan-preflight-batch` to inspect every PDF in a corpus before extraction, benchmarking, or notebook execution.

```bash
akilan-preflight-batch data \
  --report artifacts/preflight/data.json
```

The command recursively discovers `*.pdf` files by default, normalizes their paths, and evaluates each source through the same read-only preflight boundary used by `akilan-preflight`.

## Exit contract

| Exit code | Meaning |
|---|---|
| `0` | At least one PDF was discovered and every source is accepted. |
| `1` | The corpus is empty or at least one source is rejected. |
| `2` | Command-line usage or password-map configuration is invalid. |

Successful evidence is written to standard output. Blocking evidence is written to standard error. `--report` persists the deterministic JSON report regardless of acceptance status.

## Non-recursive inspection

```bash
akilan-preflight-batch data --no-recursive
```

This inspects only PDFs directly below `data/`.

## Encrypted sources

Provide a UTF-8 JSON object whose keys are either normalized absolute paths or paths relative to the corpus root:

```json
{
  "contracts/encrypted.pdf": "example-password"
}
```

Then run:

```bash
akilan-preflight-batch data \
  --password-map .secrets/pdf-passwords.json \
  --report artifacts/preflight/data.json
```

Password values are passed only to PyMuPDF authentication. They are never included in stdout, stderr, fingerprints, or persisted reports. Keep password maps outside version control and avoid placing them under `data/`.

## Operational guarantees

The command is deterministic and read-only. It does not:

- modify source PDFs;
- create or repair canonical artifacts;
- populate extraction caches;
- delete rejected files;
- infer missing passwords;
- weaken individual preflight rejection rules.

An empty corpus fails closed because a successful report with no inspected evidence is not operationally meaningful.
