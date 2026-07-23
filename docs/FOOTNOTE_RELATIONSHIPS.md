# Footnote relationship inference

AKILAN derives a narrow, auditable relationship between explicit bracketed footnote markers and their same-page source blocks.

## Supported contract

A block classified as `footnote` is eligible only when its text begins with an explicit marker in one of these forms:

```text
[1] Source details
[27] Source details
[a] Source details
```

A source candidate must:

- be classified as `paragraph`, `list_item`, `caption`, or `code`;
- precede the footnote definition in deterministic reading order;
- contain the exact bracketed marker as a standalone token;
- occur on the same page as the definition.

The intentionally conservative scope avoids guessing from bare numbers, punctuation, visual proximity, or cross-page coincidence.

## Emitted relationships

For every exact source match, the inference pass adds two compatibility projections:

```text
footnote.relationships["footnote_reference"] -> source block ID
source.relationships["has_footnote"] -> footnote block ID
```

The same edges are recorded under `page.metrics.relationship_evidence` with rule identifier:

```text
explicit-bracketed-footnote-marker-v1
```

Evidence confidence is `0.95` multiplied by the lower semantic confidence of the source and footnote blocks. Multiple explicit references to the same marker are retained; AKILAN does not collapse them into one guessed source.

## Abstention behavior

No edge is created when:

- the footnote does not start with a supported bracketed marker;
- the marker appears only after the definition;
- the source contains a similar bare number but not the exact token;
- the possible source is on another page;
- semantic classification does not identify a footnote definition.

Unsupported forms remain available in the canonical page evidence and can be handled by future additive rules without changing the artifact schema.

## Determinism and ownership

The relationship pass owns only `footnote_reference` and `has_footnote` edges that it generates. Re-running inference removes and regenerates those edges and their audit evidence idempotently while preserving externally owned relationships and metrics.
