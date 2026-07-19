# Document Relationships

AKILAN derives a conservative relationship graph from canonical page evidence after page-level semantic roles and reading order are available.

## Compatibility projection

Relationships remain available in the existing `TextBlock.relationships` mapping. This preserves the current artifact contract and all source geometry and content.

| Relationship | Source | Target | Meaning |
|---|---|---|---|
| `parent_heading` | heading | heading | Nearest preceding heading at a lower hierarchy level |
| `section_heading` | content block | heading | Section governing the content block, including across page boundaries |
| `contains` | heading | heading or content block | Direct inferred members of the section |
| `describes` | caption | table, image, or drawing | Nearby visual evidence described by the caption |

## Auditable edge evidence

Every inferred edge is also projected into the source page's additive metrics under:

```text
page.metrics.relationship_evidence
```

Each record contains:

```json
{
  "source_id": "p0002-text-0004",
  "target_id": "p0001-text-0008",
  "relationship": "section_heading",
  "rule_id": "active-section-membership-v1",
  "confidence": 0.91
}
```

The evidence list is deterministic, idempotent, and sorted by source, relationship, target, and rule. Cross-page edges are recorded on the source element's page; reciprocal `contains` evidence is recorded on the heading's page.

### Rule identifiers

| Rule ID | Relationship | Evidence basis |
|---|---|---|
| `heading-stack-parent-v1` | `parent_heading` | Active deterministic heading stack |
| `active-section-membership-v1` | `section_heading` | Nearest active heading in canonical reading order |
| `direct-section-containment-v1` | `contains` | Reciprocal direct section membership |
| `caption-proximity-overlap-v1` | `describes` | Vertical proximity and horizontal overlap |
| `caption-candidate-margin-v1` | abstention diagnostic | Best-vs-runner-up confidence margin |

Heading and section confidence is bounded by the lower semantic confidence of the two linked text blocks. Caption confidence combines overlap and normalized distance and is always clamped to `[0, 1]`.

## Caption candidate ranking

Eligible visuals must pass both the maximum vertical-gap gate and the minimum horizontal-overlap gate. Candidates are then ranked by the same combined confidence used for audit evidence:

1. higher combined confidence;
2. smaller vertical gap;
3. greater horizontal overlap;
4. stable element-kind rank;
5. stable element ID.

Using confidence as the primary ordering key keeps selection and ambiguity decisions internally consistent. A slightly farther visual with substantially stronger horizontal alignment can therefore outrank a narrowly overlapping visual that happens to be a few points closer. The remaining keys are deterministic tie-breakers only.

## Caption ambiguity diagnostics

When the two strongest visual candidates have a confidence margin below `0.08`, AKILAN deliberately creates no `describes` edge. Instead it records additive diagnostics under:

```text
page.metrics.relationship_ambiguities
```

Example:

```json
{
  "source_id": "p0003-text-0012",
  "relationship": "describes",
  "rule_id": "caption-candidate-margin-v1",
  "candidate_ids": ["p0003-table-0001", "p0003-table-0002"],
  "confidence_margin": 0.0,
  "minimum_margin": 0.08
}
```

Candidate identifiers are sorted, diagnostics are regenerated idempotently, and input collection order cannot change the result. The metric is additive and does not change the canonical artifact schema.

## Deterministic rules

1. Pages are processed by page index.
2. Text is processed by canonical reading order, with geometry and element ID as deterministic fallbacks.
3. Heading levels are derived only from `document_title`, `heading_1`, `heading_2`, and `heading_3`.
4. Heading state continues across page boundaries until a heading of the same or higher level replaces it.
5. Headers, footers, page numbers, and unknown blocks are not assigned to sections.
6. Captions link only when a candidate visual is close vertically, overlaps meaningfully in the horizontal axis, has the strongest combined evidence, and wins by the minimum confidence margin.
7. Existing relationship keys and page metrics not owned by this inference pass are retained.
8. Re-running inference regenerates the same owned edges, evidence, and ambiguity diagnostics without duplicates.

## Audit and uncertainty

Ambiguous caption relationships remain unlinked. The implementation does not invent section titles, summarize content, or alter source elements. Downstream systems can inspect edge evidence or abstention diagnostics together with source and target IDs, semantic roles, page geometry, and reading order.

## Current limits

- The graph records direct section membership rather than materializing a separate section object.
- Caption linkage is page-local.
- Heading levels depend on deterministic typography rules in `semantics.py`.
- Footnote, hyperlink, and reference-source association remain open issue #3 work.
