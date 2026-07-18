# Golden benchmark expectations

AKILAN validates extraction quality with **golden subsets**, not full serialized
artifact snapshots. Full snapshots are brittle across harmless serialization or
metadata changes; golden subsets define the evidence that must remain true for a
specific corpus case.

## Expectation file

Expectations are strict JSON keyed by the PDF filename:

```json
{
  "mixed-layout.pdf": {
    "min_page_count": 4,
    "max_page_count": 4,
    "min_text_block_count": 20,
    "min_table_count": 2,
    "min_image_count": 1,
    "min_ordered_element_ratio": 0.95,
    "required_semantic_roles": {
      "heading_1": 1,
      "paragraph": 10
    }
  }
}
```

Supported assertions include minimum and selected maximum counts, minimum reading
order coverage, minimum semantic-role counts, and an optional exact artifact
fingerprint. Exact fingerprints should be reserved for generated fixtures whose
complete canonical output is intentionally frozen.

## Evaluation

```python
from pathlib import Path

from akilan.benchmark import run_corpus, write_corpus_report
from akilan.benchmark_expectations import (
    assess_corpus,
    load_expectations,
    write_assessment,
)
from akilan.config import ExtractionConfig

pdfs = sorted(Path("data").rglob("*.pdf"))
report = run_corpus(
    pdfs,
    "artifacts/benchmark",
    config=ExtractionConfig(overwrite=True),
)
write_corpus_report(report, "artifacts/benchmark/report.json")

expectations = load_expectations("data/expectations.json")
assessment = assess_corpus(report, expectations)
write_assessment(assessment, "artifacts/benchmark/assessment.json")

if not assessment.passed:
    for violation in assessment.violations:
        print(violation.source, violation.metric, violation.message)
    raise SystemExit(1)
```

The assessment is deterministic and machine-readable. Every violation identifies:

- the source case;
- the failed metric;
- the expected relation;
- the observed value;
- an actionable message.

Extraction failures, missing expected cases, and ambiguous duplicate filenames are
reported as explicit violations rather than being silently skipped.

## CI policy

A corpus gate should fail when `assessment.passed` is false. The benchmark report
and assessment JSON should both be retained as CI artifacts so regression evidence
can be inspected without rerunning the corpus.

Recommended policy:

1. Use generated fixtures for exact fingerprints and edge-condition coverage.
2. Use structural minima for externally sourced or evolving test documents.
3. Add maxima only when duplicate extraction is a known regression risk.
4. Increase thresholds only after reviewing artifacts, not merely to make CI green.
5. Keep copyrighted or redistribution-restricted PDFs outside the repository.

## Adding a case

1. Place the locally approved PDF under `data/`.
2. Run the workbench or benchmark harness and inspect the rendered artifact.
3. Add only evidence-backed thresholds to the expectation JSON.
4. Run the evaluation twice to verify deterministic results.
5. Commit generated fixtures only when their provenance and redistribution rights
   are clear; otherwise commit expectations and documentation, not the PDF binary.
