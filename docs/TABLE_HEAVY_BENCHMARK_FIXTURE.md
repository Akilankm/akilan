# Table-heavy benchmark fixture

AKILAN's generated CI corpus includes `table_heavy.pdf`, a copyright-free ruled-table case produced entirely with PyMuPDF.

## Purpose

The fixture exercises native `Page.find_tables()` detection against deterministic geometry containing:

- a spanning title row;
- four stable columns;
- a header row;
- five data rows with text and numeric values;
- a note outside the table boundary.

The source PDF is generated during CI and does not rely on third-party copyrighted material.

## Machine-readable evidence

`scripts/generate_ci_benchmark_corpus.py` reopens every generated PDF and records page-level native table counts:

```json
{
  "page_number": 1,
  "table_count": 1
}
```

The exact count is derived from the persisted document through `page.find_tables().tables`. Focused tests additionally verify that extracted cells retain the generated title, header, and status values.

## Local reproduction

```bash
python scripts/generate_ci_benchmark_corpus.py artifacts/ci-corpus \
  --evidence artifacts/ci-benchmark/generated-corpus.json

akilan benchmark artifacts/ci-corpus \
  --output-root artifacts/ci-benchmark/artifacts \
  --report artifacts/ci-benchmark/report.json \
  --acceptance-report artifacts/ci-benchmark/acceptance.json \
  --min-ordered-element-ratio 0.75 \
  --no-cache
```

This fixture is additive, changes no canonical artifact field, and introduces no runtime dependency beyond PyMuPDF.
