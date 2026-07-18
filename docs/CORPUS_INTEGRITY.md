# Public corpus integrity

AKILAN's public benchmark corpus is declared in `data/sources.json`. Every production source entry must include a lowercase 64-character SHA-256 digest.

## Why checksums are mandatory

A stable URL does not guarantee stable bytes. Publishers may replace, regenerate, optimize, or redirect a PDF while retaining the same address. Silent upstream drift can change extraction counts, artifact fingerprints, renderings, timing measurements, and golden acceptance results.

Checksum pinning makes the benchmark input contract explicit:

- the downloaded bytes must match the reviewed source revision;
- an existing local PDF is reused only when its digest matches;
- unexpected upstream changes fail loudly before artifact generation;
- benchmark regressions can be attributed to code or configuration rather than unnoticed corpus drift.

## Updating a source

1. Download the PDF from the declared HTTPS URL.
2. Confirm the attribution page and redistribution/testing purpose remain appropriate.
3. Calculate the complete file SHA-256 digest.
4. Update only the matching manifest entry.
5. Run `pytest` and the PDF workbench.
6. Review resulting artifact and golden-metric changes in a dedicated PR.

Do not weaken or remove a checksum merely to make a changed upstream file download successfully. Treat that event as a corpus revision requiring review.

## Current pinned corpus

The manifest currently includes a small W3C baseline PDF and the multi-column *Attention Is All You Need* paper. The files themselves are acquired by the workbench or `sync_corpus()` and are not required to be committed as repository binaries.
