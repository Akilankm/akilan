# Performance regression gate

AKILAN records corpus performance evidence, but absolute timings vary across machines. The regression gate compares a current run with an approved baseline from the same workload and applies explicit relative tolerances.

```python
from akilan.benchmark_summary import CorpusPerformanceSummary
from akilan.performance_regression import (
    PerformanceRegressionThresholds,
    compare_corpus_performance,
)

report = compare_corpus_performance(
    current=current_summary,
    baseline=approved_baseline,
    thresholds=PerformanceRegressionThresholds(
        min_pages_per_second_ratio=0.80,
        max_elapsed_seconds_increase_ratio=0.25,
        max_output_size_increase_ratio=0.25,
        max_peak_memory_increase_ratio=0.25,
    ),
)

if not report.passed:
    raise RuntimeError(report.to_dict())
```

## Workload equivalence

Relative comparisons are meaningful only when both summaries describe the same workload. The gate therefore requires exact equality for:

- measured benchmark case count;
- total source bytes;
- successfully materialized page count.

A mismatch fails closed with `performance-workload-equivalence-v1`. Relative performance rules are not evaluated against a different corpus.

## Regression rules

For equivalent workloads, the gate evaluates:

- minimum retained pages-per-second ratio;
- maximum elapsed-time increase ratio;
- maximum artifact-output-size increase ratio;
- maximum peak Python-memory increase ratio.

Violations are emitted in deterministic metric order and include the baseline value, current value, expected boundary, stable rule identifier, and actionable message.

## Baseline policy

A baseline is engineering evidence, not a release decision. Store it with the environment description, Python version, PyMuPDF version, extraction configuration, source-guard fingerprint, and corpus-performance report. Refresh it only after an intentional reviewed change. Do not compare runs from materially different machines or workloads.

This boundary is additive, read-only, dependency-free, and does not modify the canonical artifact schema.
