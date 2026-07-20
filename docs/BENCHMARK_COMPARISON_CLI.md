# Benchmark comparison CLI

Use the persisted-report comparator as a fail-closed CI gate after generating a candidate benchmark report.

```bash
python scripts/compare_benchmark_reports.py \
  artifacts/baseline/report.json \
  artifacts/candidate/report.json \
  --report artifacts/candidate/comparison.json \
  --max-elapsed-increase-ratio 0.15 \
  --max-memory-increase-ratio 0.10 \
  --max-throughput-decrease-ratio 0.15
```

## Exit contract

- `0`: every baseline-successful case remains successful and all configured budgets pass.
- `1`: one or more deterministic regressions were detected.
- `2`: thresholds or benchmark evidence are invalid or unreadable.

Passing evidence is written to standard output. Regression and validation evidence is written to standard error. `--report` persists the deterministic comparison document for CI retention and later audit.

Ratios are decimal fractions. For example, `0.15` permits a 15% elapsed-time or memory increase and a 15% throughput decrease. Defaults are zero, so omitting a threshold allows no regression for that metric.

## Operational guidance

Compare reports produced from equivalent corpora, extraction configuration, cache mode, Python version, and runner class. Wall-clock and allocation metrics are sensitive to environmental variance; derive budgets from repeated controlled baselines and retain enough headroom to avoid treating normal runner noise as a product regression.

The comparator is read-only. It does not modify benchmark reports, cached artifacts, canonical artifact evidence, or the artifact schema. PyMuPDF remains the only runtime dependency.
