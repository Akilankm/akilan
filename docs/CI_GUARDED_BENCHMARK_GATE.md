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

The existing `ci-benchmark-evidence` workflow artifact uploads the guard report together with:

- generated corpus PDFs and generation evidence;
- benchmark corpus report;
- acceptance report;
- generated canonical artifacts;
- notebook and user-feedback contract reports.

## Failure semantics

The guarded command must complete successfully before artifact validation runs. If preflight rejects any selected PDF, no benchmark output root, corpus report, acceptance report, or cache marker is created. The optional guard report remains available as the concise failure explanation.

A dedicated CI step parses the persisted guard report and fails unless the corpus is accepted, every discovered source is accepted, no source is rejected, and the deterministic fingerprint is present. This locks the source-guard evidence contract without introducing another runtime or development dependency.
