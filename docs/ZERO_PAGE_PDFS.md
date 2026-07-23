# Zero-page PDF handling

AKILAN treats a structurally valid PDF whose page tree contains zero pages as an invalid extraction input.

## Contract

`PDFArtifactBuilder.build()` raises `PDFExtractionError` with a stable, actionable message before page extraction or artifact publication begins:

```text
The PDF contains no pages
```

This behavior is intentionally fail-closed. A zero-page document cannot produce meaningful page evidence, reading order, statistics, or projections, so publishing an apparently complete empty artifact would be misleading to downstream systems.

## Atomic-output guarantee

The check runs inside the staging build. When extraction targets an existing artifact directory with `overwrite=True`:

- the existing artifact remains untouched;
- no `document.json`, manifest, page artifact, or cache record is published;
- the temporary staging directory is removed;
- no backup directory is left behind.

## Regression fixture

The focused test constructs a minimal, structurally valid PDF 1.7 file with a catalog and a page tree whose `/Count` is `0`. It verifies both PyMuPDF's observed `page_count == 0` and AKILAN's fail-closed publication behavior.

This handling uses only the Python standard library and PyMuPDF and does not change the canonical artifact schema.
