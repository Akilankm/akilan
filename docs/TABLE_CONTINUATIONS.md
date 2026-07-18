# Cross-page table continuations

AKILAN preserves every native `Page.find_tables()` result and derives a separate, additive relationship projection for likely table fragments that continue onto the immediately following page.

## Evidence rules

A continuation is emitted only when all of the following hold:

1. The source and target pages are adjacent.
2. The source table reaches the bottom 22% of its page.
3. The target table begins in the top 22% of the following page.
4. Both fragments have the same positive column count.
5. Their horizontal overlap is at least 72% of the wider fragment.

A repeated first row increases confidence but is not required. Header comparison is deterministic and tolerant of common PDF extraction noise:

- matching is case-insensitive;
- punctuation and line-break differences are ignored;
- each aligned header cell is compared using token-level F1 overlap;
- the row score is the mean score of non-empty aligned cells;
- a score of at least `0.8` is treated as a repeated header.

This allows `Unit price (USD)` to match `Unit price` while preventing unrelated rows such as `Product / Value` and `Region / Quarter` from receiving a header bonus. The rule never merges, edits, hides, or replaces the source tables.

## Artifact projection

Each affected page receives an additive `metrics.table_continuations` list. Every relationship contains:

| Field | Meaning |
|---|---|
| `source_table_id` | Native table fragment on the earlier page |
| `target_table_id` | Native table fragment on the following page |
| `group_id` | Stable relationship identity derived from both table IDs |
| `confidence` | Deterministic score in the range 0–1 |
| `repeated_header` | Whether the normalized first-row similarity reaches the threshold |
| `header_similarity` | Mean token-F1 similarity of aligned non-empty header cells |
| `column_count` | Shared detected column count |
| `rule_id` | Versioned inference rule identifier |

The same relationship is projected onto both participating pages so page-local JSON remains independently auditable.

## Conservative behavior

- Candidates with mismatched columns or weak horizontal alignment remain unlinked.
- Matching is one-to-one and deterministic when multiple tables occur near page boundaries.
- Non-adjacent pages are never linked.
- Re-running inference produces identical output and does not duplicate metrics.
- Header similarity changes only confidence evidence; it cannot create a continuation without the page-boundary, column-count, and alignment gates.
- Borderless-table discovery and semantic merging remain separate future work.
