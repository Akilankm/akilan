# Deterministic Page Selection

Large enterprise PDFs can be processed as an explicit subset without renumbering source pages.

```python
from akilan import (
    ExtractionConfig,
    PDFArtifactBuilder,
    parse_page_selection,
)

artifact = PDFArtifactBuilder(
    ExtractionConfig(
        page_numbers=parse_page_selection("2,5-6"),
        overwrite=True,
    )
).build("data/large-report.pdf", "artifacts/selected-pages")
```

`parse_page_selection()` accepts comma-separated one-based page numbers and inclusive ranges. It returns the ascending tuple required by `ExtractionConfig.page_numbers`.

The parser deliberately rejects empty tokens, zero or negative pages, descending ranges, duplicate or overlapping selections, out-of-order selections, incomplete ranges, and non-integer tokens. Ambiguous input is never silently reordered or deduplicated because page selection participates in cache identity and artifact ordering.

`page_numbers` remains an ascending tuple of unique, positive, one-based source page numbers. Invalid or out-of-range selections fail before publication. Atomic output handling therefore preserves the previous known-good artifact.

## Artifact evidence

Selected pages retain their original `page_index`, `page_number`, file names, links, geometry, and element IDs. The document metadata records:

- `page_count`: total source PDF pages;
- `extracted_page_count`: pages included in this artifact;
- `extracted_page_numbers`: exact one-based source pages included;
- `is_partial_extraction`: whether the artifact omits any source page.

Artifact statistics describe only the extracted subset. This prevents a partial artifact from being silently represented as a complete document while keeping the existing schema compatible through additive metadata.

## Operational guidance

Use page selection for targeted debugging, controlled memory use, and staged inspection of very large PDFs. Do not combine independently produced subsets by concatenating JSON. Cross-page semantics, repeated margins, and table continuation are inferred only across pages present in the current build. A future resumable-build workflow should reconcile subsets through an explicit validated merge operation.

The parser uses only the Python standard library. PyMuPDF remains AKILAN's only runtime dependency, and the canonical artifact schema is unchanged.
