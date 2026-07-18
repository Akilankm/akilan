# Layout analysis and reading order

AKILAN reconstructs reading order from native PDF geometry. It does not ask an LLM to infer page structure.

## Separator evidence

Column separators are inferred from persistent vertical whitespace between element edges. A candidate separator is retained only when:

- the whitespace interval is at least 4% of page width;
- at least two eligible elements exist on each side;
- the separator is sufficiently distinct from another selected separator.

At most two separators are selected in the current implementation, supporting one-, two-, and three-column page regions.

This edge-based method avoids a failure mode in center-gap clustering where a centered figure, callout, or table creates two artificial columns.

## Spanning elements

An element is treated as spanning when it is wide relative to the page or materially crosses an inferred separator. Material crossing requires geometry on both sides of the separator, which prevents minor bounding-box noise from changing the reading order.

Spanning elements split the page into vertical bands. AKILAN partitions column content by each element's vertical center, emits the completed column band column by column, and then emits the spanning element. Center-based partitioning is deliberate: a column element whose bounding box overlaps a full-width title, callout, figure, or table is assigned to the nearest defensible band instead of being stranded and appended after a later span.

Ordering ties are resolved deterministically using column index, top coordinate, left coordinate, and stable element ID. Reversing the input element sequence therefore does not change the reconstructed order.

## Diagnostics

`akilan.layout.analyze_layout()` returns deterministic evidence without changing the canonical artifact schema:

- inferred separator coordinates;
- inferred column count;
- element IDs classified as spanning;
- element IDs with weak separator assignments;
- element counts assigned to each column.

The diagnostics are intended for benchmark assertions and engineering review. Ambiguous elements are reported rather than silently presented as high-confidence structure.

## Current limits

The current slice does not yet model nested sidebars, rotated writing directions, or independent column systems inside separate horizontal regions. Those cases remain tracked under issue #4 and should be implemented only with generated regression fixtures and corpus evidence.
