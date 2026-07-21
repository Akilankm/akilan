# Benchmark preflight CLI

Use the installed preflight gate before a benchmark run when invalid source files must be rejected before extraction creates benchmark artifacts.

```bash
akilan-benchmark-preflight data \
  --pattern '*.pdf' \
  --report artifacts/benchmark-preflight.json
```

The command recursively discovers matching files in deterministic normalized-path order and applies the same read-only PDF diagnostics used by `akilan-preflight`.

## Exit codes

- `0`: at least one PDF matched and every PDF is ready for extraction.
- `1`: no PDF matched or one or more PDFs were rejected.
- `2`: the corpus path or command configuration is invalid.

## Evidence

The JSON payload contains the corpus path, glob pattern, stable ordered entries, accepted and rejected counts, per-status counts, and a canonical SHA-256 fingerprint. Passing evidence is written to standard output; blocking evidence is written to standard error. `--report` persists the same deterministic payload before the display-only report path is appended.

## Safety boundary

The command is intentionally separate from benchmark extraction. It does not create artifact directories, write benchmark caches, repair PDFs, or modify source files. This allows CI and operators to enforce source readiness before invoking:

```bash
akilan benchmark data \
  --output-root artifacts/benchmark \
  --report artifacts/benchmark/report.json \
  --no-cache
```

Encrypted PDFs are rejected unless they are separately authenticated through an approved credential workflow. Password values are never accepted by or included in this command's evidence.
