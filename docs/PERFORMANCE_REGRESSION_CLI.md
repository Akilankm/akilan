# Performance regression CLI

`akilan-performance-regression` is a fail-closed operational gate for comparing a current corpus performance report with an explicitly approved baseline.

```bash
akilan-performance-regression \
  baselines/linux-python312-pymupdf126.json \
  artifacts/ci-benchmark/performance.json \
  --report artifacts/ci-benchmark/performance-regression.json
```

## Contract

The command reads the deterministic JSON emitted by `akilan-guarded-benchmark --performance-report`. Both reports must describe the same workload:

- measured benchmark case count;
- total source bytes;
- successfully materialized page count.

A workload mismatch fails closed and suppresses relative performance comparisons.

Default regression limits are:

| Metric | Default policy |
|---|---:|
| Pages per second | at least 80% of baseline |
| Total elapsed time | no more than 25% above baseline |
| Artifact output bytes | no more than 25% above baseline |
| Peak process-local Python memory | no more than 25% above baseline |

Thresholds can be overridden explicitly:

```bash
akilan-performance-regression baseline.json current.json \
  --min-pages-per-second-ratio 0.90 \
  --max-elapsed-seconds-increase-ratio 0.15 \
  --max-output-size-increase-ratio 0.10 \
  --max-peak-memory-increase-ratio 0.20
```

## Exit codes

- `0`: equivalent workload and no material regression;
- `1`: workload mismatch or one or more performance regressions;
- `2`: malformed evidence, unreadable input, or invalid threshold configuration.

Passing evidence is written to standard output. Blocking evidence is written to standard error. `--report` persists the same deterministic payload.

## Baseline governance

A baseline is meaningful only when its execution context is recorded and controlled. Store it with evidence for:

- operating system and machine/runner class;
- Python version;
- PyMuPDF version;
- AKILAN commit or package version;
- extraction configuration;
- source-guard fingerprint;
- cache mode.

Do not compare reports from different hardware classes, corpus identities, extraction profiles, or cache modes and interpret the result as a product regression.

The command is read-only. It does not modify PDFs, artifacts, benchmark reports, caches, or the approved baseline.
