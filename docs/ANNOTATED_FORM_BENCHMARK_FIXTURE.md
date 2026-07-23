# Annotated form benchmark fixture

AKILAN's generated CI corpus includes `annotated_form.pdf`, a copyright-free interactive-document case produced entirely with PyMuPDF.

## Purpose

The fixture validates that benchmark and extraction workflows preserve two evidence classes that are frequently lost by text-only PDF pipelines:

- a review annotation with deterministic content and geometry;
- an AcroForm text widget with a stable field name, label, type, rectangle, and value.

The fixture is generated during CI and does not require a checked-in third-party PDF.

## Generated evidence

`scripts/generate_ci_benchmark_corpus.py` records page-level counts in `generated-corpus.json`:

```json
{
  "page_number": 1,
  "annotation_count": 1,
  "widget_count": 1
}
```

The persisted PDF is reopened before evidence is collected. Counts therefore describe the saved document rather than transient in-memory objects.

Focused tests also reopen the PDF and verify:

- annotation content;
- widget field name;
- widget value;
- widget type;
- zero annotation and widget counts for non-interactive corpus cases.

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
