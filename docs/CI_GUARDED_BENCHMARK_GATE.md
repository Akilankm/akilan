# CI guarded benchmark gate

The Python 3.12 CI job runs the generated benchmark corpus through `akilan-guarded-benchmark` rather than the mixed-success `akilan benchmark` command.

## Why this boundary exists

The generated corpus is a controlled regression input. Every selected PDF must be extraction-ready before CI creates benchmark artifacts or cache evidence. Missing, malformed, encrypted, zero-page, or otherwise rejected sources therefore block the complete benchmark run instead of becoming an individual failed case inside an otherwise published corpus report.

This does not change the public mixed-success benchmark API. `akilan benchmark` remains suitable for exploratory corpora where per-file failure isolation is intentional.

## Evidence

CI persists the exact accepted source set to:

```text
artifacts/ci-benchmark/source-guard.json
```

The report contains normalized source diagnostics, aggregate counts, and a deterministic source-set fingerprint. Password values are never part of guard evidence.

CI also persists aggregate corpus-performance evidence to:

```text
artifacts/ci-benchmark/performance.json
```

The performance report records measured case count, cache-hit ratio, elapsed time, source and output byte volume, materialized page count, throughput, peak process-local Python memory, and deterministic phase totals. The CI validation step requires non-negative measurements, a non-empty generated corpus, positive source/output byte volume, and an exact match between the guarded source count and measured case count.

The existing `ci-benchmark-evidence` workflow artifact uploads both reports together with:

- generated corpus PDFs and generation evidence;
- benchmark corpus report;
- acceptance report;
- generated canonical artifacts;
- notebook and user-feedback contract reports.

## Failure semantics

The guarded command must complete successfully before artifact validation runs. If preflight rejects any selected PDF, no benchmark output root, corpus report, acceptance report, performance report, or cache marker is created. The optional guard report remains available as the concise failure explanation.

A dedicated CI step parses the persisted guard and performance reports. It fails unless the corpus is accepted, every discovered source is accepted, no source is rejected, the deterministic fingerprint is present, every guarded case has performance evidence, and all performance measurements satisfy the evidence contract. This locks the source and performance observability boundary without introducing another runtime or development dependency.
