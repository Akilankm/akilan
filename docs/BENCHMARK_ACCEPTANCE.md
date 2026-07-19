# Benchmark acceptance thresholds

A benchmark report is useful only when it can be converted into an explicit, repeatable engineering decision. AKILAN therefore provides a dependency-free acceptance layer for `CorpusReport`.

```python
from akilan import (
    BenchmarkThresholds,
    evaluate_corpus,
    write_benchmark_acceptance_report,
)
from akilan.benchmark import run_corpus

report = run_corpus(pdf_paths, "artifacts/benchmark")
acceptance = evaluate_corpus(
    report,
    BenchmarkThresholds(
        min_success_rate=1.0,
        min_ordered_element_ratio=0.99,
        min_pages_per_second=1.0,
        max_output_to_source_ratio=20.0,
    ),
)
write_benchmark_acceptance_report(
    acceptance,
    "artifacts/benchmark/acceptance.json",
)

if not acceptance.passed:
    raise SystemExit(acceptance.to_dict())
```

## Supported gates

- `min_success_rate`: minimum fraction of corpus cases that must complete successfully.
- `min_ordered_element_ratio`: minimum reading-order coverage for each successful artifact.
- `min_pages_per_second`: minimum per-case page throughput.
- `max_output_to_source_ratio`: optional maximum artifact expansion ratio.

The defaults are intentionally conservative: every case must pass and every readable element must be represented in reading order, while performance and output expansion are not constrained until the project records environment-specific baselines.

All configured thresholds must be finite. `NaN`, positive infinity, and negative infinity are rejected during policy construction because normal numeric comparisons can otherwise allow invalid values to bypass a quality gate.

## Evidence contract

A case marked `passed` must contain both artifact metrics and performance metrics. Missing evidence is itself an acceptance violation. Failed cases retain their original error message. Numeric evidence used by a gate must also be finite; invalid values are emitted as explicit violations rather than silently accepted.

Violations are deterministic and machine-readable:

```json
{
  "source": "data/public/complex.pdf",
  "metric": "ordered_element_ratio",
  "expected": ">= 0.990000",
  "actual": 0.94,
  "message": "ordered element coverage is below the required threshold",
  "rule_id": "benchmark-ordered-element-ratio-v1"
}
```

Stable rule identifiers allow CI systems to distinguish extraction failures, missing evidence, finite-value violations, and threshold failures without parsing human-readable messages.

An empty corpus fails explicitly with `benchmark-corpus-nonempty-v1`. Corpus-level violations are reported first using the synthetic source `$corpus`; case-level violations are then sorted by source, metric, and rule identifier. This makes reports stable across supported Python versions and suitable for CI comparison.

`write_benchmark_acceptance_report()` writes sorted, indented JSON with a trailing newline. The report contains only operational benchmark evidence; it does not modify the canonical artifact schema or cache identity.

Thresholds should be tightened only from measured corpus evidence. Machine-dependent throughput gates should be calibrated per CI runner class rather than copied blindly between environments. This policy adds no runtime dependency beyond PyMuPDF.
