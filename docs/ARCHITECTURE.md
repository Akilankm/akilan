# Architecture

## Pipeline

```text
PDF bytes
  │
  ├─ document identity and metadata
  │
  └─ page iteration
       ├─ raw text dictionary → blocks / lines / spans / optional characters
       ├─ native table finder → tables / cells / rows
       ├─ image XObjects + rawdict image blocks → assets / occurrences
       ├─ vector drawing paths → drawing elements
       ├─ links / annotations / widgets
       ├─ page-local semantic classification
       └─ geometry-first reading-order reconstruction
             │
             ├─ repeated margin analysis across pages
             └─ artifact writer
                  ├─ canonical JSON
                  ├─ Markdown projection
                  ├─ plain-text projection
                  └─ optional page renders
```

## Canonical versus projected representations

The canonical representation is JSON. Markdown and plain text are generated projections and may omit headers, footers, vector decorations, and other non-prose evidence. Downstream AI systems that need traceability should retain element IDs from page JSON.

## Stable identifiers

IDs are deterministic inside a specific extraction run and encode page and source order. Future schema versions may introduce content-addressed IDs; consumers should treat IDs as opaque strings.

## Geometry model

All coordinates use PyMuPDF's unrotated page coordinate system in PDF points. Every page records media and crop boxes so coordinates remain interpretable. Normalized geometry can be derived from `BBox.normalized()`.

## Reading order

The first implementation combines:

- inferred column separators from x-center whitespace;
- full-width spanning elements as vertical band separators;
- column-major ordering inside each band;
- table-overlap suppression for duplicate text blocks;
- materiality filtering for vector drawings.

The raw elements remain available even when excluded from reading order.

## Planned layers

1. relationship graph: captions, callouts, footnotes, cross-references;
2. section hierarchy across pages;
3. repeated visual templates and page archetypes;
4. deterministic table continuation detection;
5. benchmark corpus and extraction quality metrics;
6. incremental artifacts and content-addressed caching.
