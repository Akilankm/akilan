# Benchmark elapsed-time CLI budget

AKILAN can enforce an optional wall-clock elapsed-time budget for each successful benchmark case.

```bash
akilan benchmark data \
  --output-root artifacts/benchmark \
  --report artifacts/benchmark/report.json \
  --acceptance-report artifacts/benchmark/acceptance.json \
  --max-elapsed-seconds 30 \
  --no-cache
```

`--max-elapsed-seconds` is disabled when omitted. When configured, every successful benchmark case must report finite, non-negative elapsed-time evidence and must not exceed the supplied limit. A violation causes the command to return exit code `1` and is included in the machine-readable acceptance report under the stable rule `benchmark-elapsed-time-v1`.

## Operational guidance

Wall-clock measurements include filesystem, interpreter, runner, and host effects. Treat this option as a regression budget rather than a universal performance claim:

- use `--no-cache` when validating extraction cost;
- run on a controlled runner class;
- establish the budget from repeated baseline measurements;
- include headroom for expected machine variance;
- evaluate throughput and peak Python allocation alongside elapsed time.

The threshold does not change extraction behavior, artifact contents, or the canonical artifact schema. PyMuPDF remains the only runtime dependency.
