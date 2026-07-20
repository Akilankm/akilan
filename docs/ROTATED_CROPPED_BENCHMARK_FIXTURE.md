# Rotated and cropped benchmark fixture

AKILAN's generated CI corpus includes `rotated_cropped.pdf`, a copyright-free geometry case produced entirely with PyMuPDF.

## Purpose

The fixture verifies that extraction and benchmark workflows retain three distinct page concepts:

- the physical media box;
- the visible crop box;
- the page rotation applied by a PDF viewer.

The page contains deterministic text and vector evidence inside an inset crop region and is presented with a 90-degree clockwise rotation. A correct artifact must preserve the source geometry rather than normalizing these values away.

## Generated evidence

`scripts/generate_ci_benchmark_corpus.py` records per-page evidence in `generated-corpus.json`:

```json
{
  "page_number": 1,
  "rotation": 90,
  "media_box": [0.0, 0.0, 595.0, 842.0],
  "crop_box": [36.0, 54.0, 559.0, 788.0]
}
```

Exact A4 floating-point dimensions are supplied by the installed PyMuPDF version. Tests assert semantic properties—90-degree rotation and a crop box distinct from the media box—rather than duplicating implementation-specific serialization.

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

The fixture is additive, changes no canonical artifact field, and introduces no runtime dependency beyond PyMuPDF.
