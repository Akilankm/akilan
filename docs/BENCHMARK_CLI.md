# Corpus benchmark CLI

AKILAN provides a dependency-free command-line entry point for running the existing benchmark harness over every matching PDF in a directory.

```bash
akilan benchmark data \
  --output-root artifacts/benchmark \
  --report artifacts/benchmark/report.json
```

The command recursively discovers `*.pdf` files, isolates every document into its own collision-safe artifact directory, and writes the same deterministic JSON report produced by `akilan.benchmark.write_corpus_report`.

## Exit contract

- `0`: every discovered PDF was extracted and measured successfully.
- `1`: at least one PDF failed; the report is still written with per-file error evidence.
- non-zero `SystemExit`: the corpus directory is missing or no files match the requested pattern.

This makes the command suitable for CI quality gates without losing failure diagnostics.

## Useful options

```bash
# Force a cold performance run rather than reusing content-addressed results.
akilan benchmark data \
  --output-root artifacts/cold \
  --report artifacts/cold/report.json \
  --no-cache

# Run only a selected recursive corpus subset.
akilan benchmark data \
  --pattern "public/*.pdf" \
  --output-root artifacts/public \
  --report artifacts/public/report.json

# Produce page renders while retaining PyMuPDF as the only runtime dependency.
akilan benchmark data \
  --output-root artifacts/rendered \
  --report artifacts/rendered/report.json \
  --render-pages \
  --render-dpi 144
```

Extraction flags mirror the existing `extract` command: character geometry, page rendering, DPI, and optional table, image, or drawing extraction can be controlled explicitly.

## Recommended validation flow

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
akilan benchmark data \
  --output-root artifacts/benchmark \
  --report artifacts/benchmark/report.json
```

The benchmark report is operational evidence and remains outside the canonical document artifact schema.
