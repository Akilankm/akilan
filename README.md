# AKILAN

**Adaptive Knowledge Ingestion and Layout Analysis**

AKILAN converts a PDF into a deterministic, geometry-aware artifact for AI systems. It uses **PyMuPDF as its only runtime dependency** and preserves the native evidence required to reason about a document instead of flattening every page into plain text.

## What the artifact captures

| Layer | Native PyMuPDF evidence | Artifact output |
|---|---|---|
| Document | metadata, permissions, page mode/layout, TOC, embedded files | `manifest.json`, `document.json` |
| Page geometry | media box, crop box, rotation, labels, dimensions | per-page JSON |
| Text | blocks, lines, spans, fonts, sizes, colors, flags, bounding boxes | structured JSON + Markdown + text |
| Tables | `Page.find_tables()` geometry and cell content | rows, cells, Markdown, reading-order references |
| Images | XObjects, inline image blocks, occurrences, transforms, dimensions | extracted binary assets + geometry |
| Vector graphics | paths, fills, strokes, layers, sequence numbers | drawing elements in page JSON |
| Interactivity | links, annotations, widgets/form fields | typed page elements |
| Semantics | typography, margins, repetition, columns, spatial overlap | deterministic roles and reading order |

No LLM, cloud service, OCR engine, computer-vision model, Pillow, Camelot, or pdfplumber is required.

## Installation

```bash
pip install -e ".[dev]"
```

## Python API

```python
from akilan import ExtractionConfig, PDFArtifactBuilder

config = ExtractionConfig(
    render_pages=True,
    include_characters=False,
    overwrite=True,
)

artifact = PDFArtifactBuilder(config).build(
    "document.pdf",
    "artifacts/document",
)

print(artifact.statistics)
```

A convenience function is also available:

```python
from akilan import build_artifact

artifact = build_artifact("document.pdf", "artifacts/document")
```

## CLI

```bash
akilan extract document.pdf \
  --output artifacts/document \
  --render-pages \
  --overwrite
```

## Artifact layout

```text
artifacts/document/
├── manifest.json
├── document.json
├── document.md
├── document.txt
├── pages/
│   ├── page_0001.json
│   ├── page_0001.md
│   └── ...
└── assets/
    ├── images/
    │   └── ...
    └── renders/
        └── page_0001.png
```

### `manifest.json`

A compact index containing source identity, schema version, extraction engine, aggregate metrics, and paths to every generated artifact.

### `document.json`

The complete machine-readable document graph. Every major element has a stable page-scoped ID, a bounding box, and native properties. Reading-order entries reference these IDs rather than duplicating content.

### Page JSON

Each page retains:

- text block → line → span hierarchy;
- optional character-level geometry;
- table cell geometry and extracted rows;
- image occurrences and reusable extracted assets;
- vector drawings;
- links, annotations, and form fields;
- deterministic semantic roles;
- interleaved geometry-aware reading order.

## Semantic inference

AKILAN does not claim model-generated semantic understanding. It derives reproducible structural semantics from measurable PDF evidence:

1. typography relative to the page body-font distribution;
2. location in header/footer margins;
3. repeated margin content across pages;
4. list and page-number patterns;
5. monospaced-font detection;
6. table overlap suppression;
7. column boundaries and spanning regions.

Each text block includes `semantic_role` and `semantic_confidence`, making heuristic decisions explicit and auditable.

## Design principles

- **Evidence first:** never discard geometry merely to produce cleaner prose.
- **Deterministic:** the same PDF and configuration produce the same schema and ordering.
- **AI friendly:** JSON is normalized; Markdown and plain text are projections, not the source of truth.
- **PyMuPDF native:** use the engine's document, page, text, table, image, drawing, link, annotation, and widget APIs directly.
- **Inspectable:** page renders and stable IDs make extraction decisions debuggable.
- **Extensible:** future semantic passes should add relationships without mutating source evidence.

## Development

```bash
python -m pytest
ruff check .
python -m build
```

## License note

AKILAN's source is currently MIT licensed. PyMuPDF is a separately licensed dependency offered under AGPL and commercial terms. Review the PyMuPDF licensing requirements before embedding this library in proprietary or network-accessible software.
