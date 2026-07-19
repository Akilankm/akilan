# Footnote input validation

AKILAN exposes a read-only validation API for detecting page-local duplicate explicit footnote definitions before relationship inference or downstream consumption.

```python
from akilan import find_duplicate_footnote_markers

conflicts = find_duplicate_footnote_markers(document.pages)
for conflict in conflicts:
    print(conflict.to_dict())
```

A conflict is reported only when more than one text block classified as `footnote` begins with the same supported bracketed marker, such as `[1]` or `[a]`, on the same page.

## Contract

- Matching is case-insensitive for alphabetic markers.
- Numeric markers support one to three digits.
- Bare numbers and non-footnote text blocks are ignored.
- Detection is page-local; marker reuse on different pages is not treated as a conflict.
- Results are deterministic across page and block input order.
- The validator never mutates the artifact.
- The stable diagnostic rule identifier is `duplicate-footnote-definition-marker-v1`.

This additive validation boundary prevents ambiguous source material from being silently treated as unambiguous relationship evidence. It does not alter the canonical artifact schema or the existing inference output.
