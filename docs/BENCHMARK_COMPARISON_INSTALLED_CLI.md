# Installed benchmark comparison CLI

After installing AKILAN, compare persisted benchmark reports without reaching into the repository scripts directory:

```bash
akilan-compare-benchmarks \
  artifacts/baseline/report.json \
  artifacts/candidate/report.json \
  --report artifacts/candidate/comparison.json \
  --max-elapsed-increase-ratio 0.15 \
  --max-memory-increase-ratio 0.10 \
  --max-throughput-decrease-ratio 0.15
```

## Exit contract

- `0`: all baseline-successful cases remain successful and configured budgets pass.
- `1`: one or more deterministic regressions were detected.
- `2`: thresholds or benchmark evidence are invalid or unreadable.

Passing evidence is written to standard output. Regression and invalid-evidence payloads are written to standard error. The optional report is deterministic JSON suitable for CI retention.

The command is read-only: it does not modify benchmark inputs, cached artifacts, canonical PDF artifacts, or schemas. PyMuPDF remains the only runtime dependency.
