# Public PDF corpus

AKILAN keeps the benchmark corpus reproducible through `data/sources.json` rather than silently committing third-party binaries.

## Safety and reproducibility guarantees

`sync_corpus()`:

- accepts only HTTPS source and attribution URLs;
- rejects absolute paths and path traversal;
- enforces a configurable declared and streamed byte limit;
- supports optional SHA-256 pinning;
- writes into a sibling temporary file;
- flushes and fsyncs the completed download;
- validates the file with PyMuPDF and requires at least one page;
- atomically publishes the PDF only after validation;
- preserves an existing valid PDF unless `overwrite=True`;
- removes incomplete staging files after any failure.

## Download the declared corpus

Use the production CLI for repeatable local and CI workflows:

```bash
akilan-corpus sync data/sources.json --data-dir data
```

The command emits one JSON record per declared source, including status, final path, SHA-256, byte size, and page count. Use `--overwrite` only for an intentional refresh. `--timeout` and `--max-bytes` provide explicit network and storage limits.

The equivalent Python API remains available:

```python
from akilan import sync_corpus

results = sync_corpus("data/sources.json", "data")
for result in results:
    print(result.source_id, result.status, result.page_count, result.path)
```

Downloaded PDFs are intentionally ignored by Git. The manifest, source page, purpose, checksum, and downloader behavior remain reviewable while avoiding accidental redistribution of external binaries.

## Verify before testing

Verification performs no network access and fails closed when any declared PDF is missing, invalid, or checksum-inconsistent:

```bash
akilan-corpus verify data/sources.json --data-dir data
```

Successful evidence is written to standard output. Blocking evidence is written to standard error and returns exit status `1`, making the command suitable as a pre-notebook or pre-benchmark gate.

## Adding a source

Add an entry to `data/sources.json`:

```json
{
  "id": "stable-identifier",
  "url": "https://publisher.example/report.pdf",
  "filename": "public/report.pdf",
  "source_page": "https://publisher.example/report",
  "purpose": "Specific extraction capability exercised by this document",
  "sha256": "optional-64-character-lowercase-digest"
}
```

Prefer publisher-controlled URLs, stable source pages, explicit public-access terms, and checksum pinning when the publisher provides immutable files. A source manifest is not a licensing determination; maintainers must still respect the publisher's terms.

## Notebook workflow

`notebooks/pdf_artifact_workbench.ipynb` synchronizes the manifest, discovers all `data/**/*.pdf` files, renders pages, builds artifacts, and writes `artifacts/notebook/validation_report.json`.
