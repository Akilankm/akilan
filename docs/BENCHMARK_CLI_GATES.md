# Benchmark CLI acceptance gates

The `akilan benchmark` command can enforce deterministic quality and performance requirements directly from shell scripts and CI jobs.

## Example

```bash
akilan benchmark data/public \
  --output-root artifacts/benchmark \
  --report artifacts/benchmark/corpus-report.json \
  --acceptance-report artifacts/benchmark/acceptance-report.json \
  --min-success-rate 1.0 \
  --min-ordered-element-ratio 0.99 \
  --min-pages-per-second 1.0 \
  --max-output-to-source-ratio 20.0
```

The command exits with code `0` only when every configured acceptance gate passes. It exits with code `1` when extraction fails or a quality or performance threshold is violated.

## Thresholds

| Option | Default | Meaning |
|---|---:|---|
| `--min-success-rate` | `1.0` | Minimum successful-case fraction across the corpus. |
| `--min-ordered-element-ratio` | `1.0` | Minimum reading-order coverage required for every successful artifact. |
| `--min-pages-per-second` | `0.0` | Minimum extraction throughput required for every successful case. |
| `--max-output-to-source-ratio` | unset | Optional maximum persisted artifact size divided by source PDF size. |

Invalid thresholds are rejected before extraction starts.

## Machine-readable evidence

The standard output summary includes:

- corpus report path;
- optional acceptance report path;
- total, successful, and failed case counts;
- overall acceptance state;
- stable violation records containing source, metric, expected value, actual value, and message.

When `--acceptance-report` is supplied, the complete acceptance result is written as deterministic JSON. This file is suitable for CI artifact retention and downstream release checks.

### Publication integrity

Acceptance reports are published atomically in the destination directory. AKILAN writes and flushes a temporary file before replacing the destination with `os.replace()`. Existing reports therefore remain readable until the new JSON is complete, and failed serialization or publication removes the temporary file without damaging the previous report.

This guarantee applies to acceptance-report publication and is intended for CI readers, artifact collectors, and concurrent monitoring processes that must never observe truncated JSON.

## Operational policy

Performance thresholds should be calibrated on controlled runners. Cache hits can produce materially different throughput from cold extraction, so use `--no-cache` when establishing or enforcing cold-run baselines.

These gates do not authorize a production release or PyPI publication. Release remains blocked by the licensing and deployment decision tracked separately.
