# Benchmark regression comparison

AKILAN benchmark acceptance answers whether one run satisfies absolute quality and performance limits. `akilan.benchmark_comparison` adds a separate baseline-comparison boundary for detecting relative performance regressions between persisted benchmark reports.

```python
from akilan.benchmark_comparison import (
    BenchmarkRegressionThresholds,
    compare_benchmark_reports,
    write_benchmark_comparison_report,
)

comparison = compare_benchmark_reports(
    "artifacts/baseline/report.json",
    "artifacts/candidate/report.json",
    BenchmarkRegressionThresholds(
        max_elapsed_increase_ratio=0.15,
        max_memory_increase_ratio=0.10,
        max_throughput_decrease_ratio=0.15,
    ),
)

write_benchmark_comparison_report(
    comparison,
    "artifacts/candidate/regression-comparison.json",
)

if not comparison.passed:
    raise SystemExit(1)
```

Ratios are decimal fractions: `0.15` permits a 15% regression. Defaults are intentionally strict (`0.0`) and should be replaced with evidence-based tolerances for the controlled runner used by the project.

## Contract

The comparator:

- considers successful cases matched by their stable `source` value;
- fails when a previously successful baseline case is missing or failed;
- compares elapsed wall time, peak Python allocations, and page throughput;
- rejects duplicate sources and malformed or non-finite performance evidence;
- emits findings in deterministic source/metric/rule order;
- never modifies either benchmark report;
- uses only the Python standard library.

A candidate-only case is recorded in the case counts but is not treated as a regression because no baseline exists. It should first pass the normal absolute benchmark acceptance gate.

## Measurement limits

Elapsed time and throughput are sensitive to runner load, CPU allocation, filesystem state, warm caches, and extraction configuration. Peak Python memory comes from `tracemalloc` and does not represent complete process RSS or every native PyMuPDF allocation. Compare reports only when the corpus, package version, extraction configuration, and runner class are equivalent.
