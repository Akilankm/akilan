# Guarded benchmark CLI

`akilan-guarded-benchmark` is the fail-closed operational boundary for benchmark runs that must not publish partial evidence from an invalid corpus.

```bash
akilan-guarded-benchmark data \
  --output-root artifacts/benchmark/artifacts \
  --report artifacts/benchmark/report.json \
  --acceptance-report artifacts/benchmark/acceptance.json \
  --guard-report artifacts/benchmark/source-guard.json \
  --performance-report artifacts/benchmark/performance.json \
  --execution-identity-report artifacts/benchmark/execution-identity.json \
  --min-ordered-element-ratio 0.75 \
  --no-cache
```

## Execution contract

Before the benchmark runner creates its output root, canonical artifact directories, or cache markers, the command preflights the exact sorted source set selected by `--pattern`.

The run is rejected when:

- no matching PDF is present;
- a source is missing, unreadable, malformed, non-PDF, encrypted, or zero-page;
- any other source-preflight diagnostic is not accepted.

A rejected run returns exit code `1`, writes deterministic guard evidence to stderr, optionally persists it through `--guard-report`, and leaves the benchmark output root, corpus report, performance report, and execution-identity report absent.

After every source passes, the command delegates to the existing benchmark runner and acceptance evaluator. When `--guard-report` is supplied, the same deterministic source evidence is persisted for successful runs. The command output includes the guard fingerprint and guarded source count so benchmark reports can be tied to the exact normalized, deduplicated source set that passed preflight.

When `--performance-report` is supplied, the command also persists deterministic corpus-level performance evidence containing:

- measured case count and cache-hit ratio;
- total wall time, source bytes, output bytes, and materialized page count;
- aggregate pages per second and source MiB per second;
- maximum observed process-local Python memory peak;
- deterministic phase-time totals.

When `--execution-identity-report` is supplied, the command persists the exact runtime and extraction context used for the performance run:

- Python implementation and version;
- operating-system family and machine architecture;
- PyMuPDF version;
- AKILAN package version;
- the complete validated `ExtractionConfig`;
- a canonical SHA-256 fingerprint and explicit validity result.

The same performance and execution-identity payloads are embedded in the command result, allowing automation to consume the evidence without reopening report files. Performance baselines should be compared only when both the source-guard fingerprint and execution-identity fingerprint match. Failed benchmark cases contribute available timing, memory, and byte-volume evidence, but only successfully materialized pages contribute to page throughput.

Acceptance failures also return exit code `1`; invalid CLI configuration returns `2` through `argparse`.

## Python audit result

Call `run_guarded_corpus_with_report()` when programmatic consumers need both readiness and benchmark evidence:

```python
from akilan.benchmark_summary import summarize_corpus_performance
from akilan.guarded_benchmark import run_guarded_corpus_with_report
from akilan.performance_execution_identity import build_performance_execution_identity

execution = run_guarded_corpus_with_report(
    ["data/a.pdf", "data/b.pdf"],
    "artifacts/benchmark",
    use_cache=False,
)

print(execution.guard_report.fingerprint)
print(execution.corpus_report.succeeded)
print(summarize_corpus_performance(execution.corpus_report).to_dict())
print(build_performance_execution_identity().to_dict())
```

The existing `run_guarded_corpus()` API remains unchanged and continues returning only `CorpusReport`.

## Deliberate encrypted-PDF behavior

The guarded runner currently rejects encrypted PDFs. Although preflight APIs can authenticate them, the benchmark extraction runner does not yet forward per-source credentials. Accepting encrypted files during preflight without forwarding those credentials would create a false readiness signal.

## Runtime and schema safety

The command introduces no runtime dependency beyond PyMuPDF. It does not alter the canonical artifact schema, modify source PDFs, repair documents, or change the existing mixed-success `akilan benchmark` behavior.
