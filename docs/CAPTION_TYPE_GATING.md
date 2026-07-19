# Explicit Caption Type Gating

AKILAN uses explicit caption labels as deterministic structural evidence when associating captions with nearby visual elements.

## Supported labels

| Caption prefix | Compatible artifact elements |
|---|---|
| `Table`, `Tab.` | native table elements |
| `Figure`, `Fig.` | images and vector drawings |

Labels are matched case-insensitively at the beginning of caption text and may be followed by Arabic or Roman numerals. Unlabelled captions retain the existing geometry-first ranking behavior.

## Selection contract

1. Candidate visuals must first pass the existing vertical-gap and horizontal-overlap gates.
2. When the caption has an explicit supported label, incompatible candidate kinds are excluded.
3. Compatible candidates remain ranked by combined proximity-and-overlap confidence and deterministic tie-breakers.
4. If eligible visuals exist but none matches the explicit caption type, AKILAN abstains rather than creating a contradictory relationship.

Type-based abstention is recorded under `page.metrics.relationship_ambiguities` with rule ID `caption-explicit-type-gate-v1`, the expected visual type, and sorted candidate IDs. This diagnostic is additive and does not change the canonical artifact schema.

## Rationale

PDF geometry alone is insufficient when a table and figure are close together. A caption such as `Table 4. Accuracy by model` is direct source evidence that the target should be a table. Treating that label as a hard compatibility gate prevents a closer image or drawing from receiving a false `describes` edge.

The rule remains conservative: it does not infer target identity from caption numbering, does not cross page boundaries, and does not invent a relationship when no compatible candidate is present.
