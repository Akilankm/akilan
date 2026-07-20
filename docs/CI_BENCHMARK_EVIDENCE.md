# CI benchmark evidence

AKILAN's unit suite validates focused invariants, while the CI benchmark smoke gate validates that the installed command-line workflow can generate and consume complete PDF artifacts end to end.

## Generated corpus

`scripts/generate_ci_benchmark_corpus.py` creates a small copyright-free corpus using PyMuPDF:

- `single_column.pdf` exercises text hierarchy, line wrapping, vector extraction, and ordinary reading order;
- `mixed_layout.pdf` exercises two-column geometry, a vertical separator, a spanning region, and combined text/vector evidence.

The generator does not download third-party documents and does not add a runtime dependency. It emits JSON evidence describing the exact case set, output paths, byte sizes, and page counts.

```bash
python scripts/generate_ci_benchmark_corpus.py artifacts/ci-corpus \
  --evidence artifacts/ci-benchmark/generated-corpus.json
```

## Acceptance gate

The Python 3.12 CI job runs a cold benchmark over the generated corpus:

```bash
akilan benchmark artifacts/ci-corpus \
  --output-root artifacts/ci-benchmark/artifacts \
  --report artifacts/ci-benchmark/report.json \
  --acceptance-report artifacts/ci-benchmark/acceptance.json \
  --min-ordered-element-ratio 0.75 \
  --no-cache
```

The gate fails when extraction fails, ordered-element coverage falls below the configured threshold, or the benchmark command cannot produce its reports. CI then validates the generated artifact directories and uploads the evidence bundle for inspection.

The ordered-element threshold is intentionally below `1.0`. AKILAN preserves decorative vector drawings as canonical source evidence even when they should not participate in reading order. Requiring every retained drawing to be ordered would reward incorrect promotion of decoration into document flow. The generated cases currently produce ratios of `0.80` and approximately `0.91`, so `0.75` remains strict enough to detect substantial reading-order loss while respecting evidence-preservation semantics.

## Evidence bundle

The `ci-benchmark-evidence` workflow artifact contains:

- generated corpus metadata;
- benchmark corpus report;
- acceptance report;
- complete generated AKILAN artifact directories.

The PDFs and artifact outputs live only in the ephemeral CI workspace and workflow artifact. They are not committed to the repository and do not change the canonical artifact schema.

## Local validation

```bash
python scripts/generate_ci_benchmark_corpus.py /tmp/akilan-ci-corpus \
  --evidence /tmp/akilan-ci-evidence/generated-corpus.json

akilan benchmark /tmp/akilan-ci-corpus \
  --output-root /tmp/akilan-ci-evidence/artifacts \
  --report /tmp/akilan-ci-evidence/report.json \
  --acceptance-report /tmp/akilan-ci-evidence/acceptance.json \
  --min-ordered-element-ratio 0.75 \
  --no-cache

find /tmp/akilan-ci-evidence/artifacts -mindepth 1 -maxdepth 1 -type d \
  -exec akilan validate {} \;
```
