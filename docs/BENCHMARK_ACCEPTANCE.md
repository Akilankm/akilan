# Benchmark acceptance thresholds

A benchmark report is useful only when it can be converted into an explicit, repeatable engineering decision. AKILAN therefore provides a dependency-free acceptance layer for `CorpusReport`.

```python
from akilan.benchmark import run_corpus
from akilan.benchmark_acceptance import BenchmarkThresholds, evaluate_corpus

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

if not acceptance.passed:
    raise SystemExit(acceptance.to_dict())
```

## Supported gates

- `min_success_rate`: minimum fraction of corpus cases that must complete successfully.
- `min_ordered_element_ratio`: minimum reading-order coverage for each successful artifact.
- `min_pages_per_second`: minimum per-case page throughput.
- `max_output_to_source_ratio`: optional maximum artifact expansion ratio.

The defaults are intentionally conservative: every case must pass and every readable element must be represented in reading order, while performance and output expansion are not constrained until the project records environment-specific baselines.

## Evidence contract

A case marked `passed` must contain both artifact metrics and performance metrics. Missing evidence is itself an acceptance violation. Failed cases retain their original error message.

Violations are deterministic and machine-readable:

```json
{
  "source": "data/public/complex.pdf",
  "metric": "ordered_element_ratio",
  "expected": ">= 0.990000",
  "actual": 0.94,
  "message": "ordered element coverage is below the required threshold"
}
```

Corpus-level violations are reported first using the synthetic source `$corpus`; case-level violations are then sorted by source and metric. This makes reports stable across supported Python versions and suitable for CI comparison.

Thresholds should be tightened only from measured corpus evidence. They do not alter the canonical artifact schema and add no runtime dependency beyond PyMuPDF.
