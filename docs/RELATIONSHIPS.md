# Document Relationships

AKILAN derives a conservative relationship graph from the canonical page evidence after page-level semantic roles and reading order are available.

## Relationship vocabulary

Relationships are stored in the existing `TextBlock.relationships` mapping. This keeps the change additive and preserves all source geometry and content.

| Relationship | Source | Target | Meaning |
|---|---|---|---|
| `parent_heading` | heading | heading | Nearest preceding heading at a lower hierarchy level |
| `section_heading` | content block | heading | Section governing the content block, including across page boundaries |
| `contains` | heading | heading or content block | Direct inferred members of the section |
| `describes` | caption | table, image, or drawing | Nearby visual evidence described by the caption |

## Deterministic rules

1. Pages are processed by page index.
2. Text is processed by canonical reading order, with geometry and element ID as deterministic fallbacks.
3. Heading levels are derived only from the existing semantic roles: `document_title`, `heading_1`, `heading_2`, and `heading_3`.
4. Heading state continues across page boundaries until a heading of the same or higher level replaces it.
5. Headers, footers, page numbers, and unknown blocks are not assigned to sections.
6. Captions link only when a candidate visual is close vertically and overlaps meaningfully in the horizontal axis.
7. Existing relationship keys not owned by this inference pass are retained.
8. Re-running inference produces the same graph without duplicate edges.

## Audit and uncertainty

The implementation deliberately leaves ambiguous caption relationships unlinked. It does not invent section titles, summarize content, or alter source elements. Downstream systems can always inspect the source and target element IDs, semantic roles, confidence values, page geometry, and reading order.

## Current limits

- The graph records direct section membership rather than materializing a separate section object.
- Caption linkage is page-local.
- Heading levels depend on the deterministic typography rules in `semantics.py`.
- Cross-page tables and figure continuations require additional evidence and remain future work.
