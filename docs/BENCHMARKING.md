# Benchmarking AKILAN artifacts

AKILAN benchmarks extraction output at the canonical artifact layer. The benchmark harness does not replace corpus-specific golden assertions; it provides deterministic coverage metrics, failure isolation, fingerprints, and process-local performance evidence that make regressions visible.

## Corpus layout

Place local validation PDFs under `data/`. PDF binaries remain outside source control unless their licensing and redistribution rights are explicit.

```text
data/
├── multi_column.pdf
├── table_heavy.pdf
└── nested/
    └── annotated_form.pdf
```

## Python workflow

```python
from pathlib import Path

from akilan.benchmark import run_corpus, write_corpus_report
from akilan.config import ExtractionConfig

pdfs = sorted(Path("data").rglob("*.pdf"))
report = run_corpus(
    pdfs,
    "artifacts/benchmark",
    config=ExtractionConfig(overwrite=True, render_pages=False),
)
write_corpus_report(report, "artifacts/benchmark/report.json")

if report.failed:
    raise SystemExit(f"{report.failed} corpus case(s) failed")
```

Each PDF is processed independently. One malformed, encrypted, or missing input is recorded as a failed case without preventing the remaining corpus from running.

## Metrics

The report records:

- source SHA-256;
- page and element counts;
- reading-order coverage;
- semantic-role distribution;
- canonical artifact fingerprint;
- elapsed extraction time;
- source and generated artifact sizes;
- pages processed per second;
- source MiB processed per second;
- generated-output-to-source size ratio;
- peak Python-tracked memory;
- structured error type and message for failed cases.

The canonical fingerprint is computed from the complete JSON-serializable artifact with sorted keys and compact separators. Running the same package, PyMuPDF version, configuration, and PDF twice should produce the same fingerprint.

### Performance interpretation

Performance values are diagnostics, not canonical artifact content. They can vary with operating system, Python version, PyMuPDF version, filesystem, CPU contention, rendering configuration, and PDF structure.

`peak_python_memory_bytes` comes from Python's `tracemalloc` facility. It measures Python-tracked allocations during the case and does not claim to represent complete process RSS or native allocations performed inside MuPDF. Use an external process profiler when release decisions require total resident-memory evidence.

Failed cases retain elapsed time, peak Python memory, and any partial output size. This makes early resource failures visible without reporting the partial directory as a complete artifact.

For stable comparisons:

1. use the same machine and Python/PyMuPDF versions;
2. keep the extraction configuration identical;
3. disable unrelated workloads;
4. compare distributions across several runs rather than treating one run as a hard guarantee;
5. investigate output-size or throughput changes together with artifact fingerprints and quality assertions.

## Golden assertions

Coverage metrics detect broad regressions but do not prove layout correctness. Each benchmark fixture should add focused expectations for the evidence that matters, such as:

- expected page count and text coverage;
- expected table row and column structure;
- expected image occurrences;
- expected reading-order relations;
- expected rotation and crop-box handling;
- expected annotation or form-widget extraction.

Prefer targeted assertions over full-file snapshots. Full snapshots become brittle when additive schema fields are introduced.

## Acceptance policy

A benchmark change is mergeable only when:

1. extraction completes for all fixtures expected to pass;
2. failures identify the source, exception type, and message;
3. repeated runs produce identical artifact fingerprints;
4. new heuristics include a fixture and a focused regression assertion;
5. performance regressions are investigated on equivalent environments and configurations;
6. no third-party PDF is committed without confirmed redistribution rights.
