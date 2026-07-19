# Document element identity validation

AKILAN relationship edges address artifact elements by their string `id`. A valid document artifact therefore requires every element ID to be non-empty and unique across the complete document, not merely within one page or collection.

Use the public read-only validator before consuming relationship graphs:

```python
from akilan import find_duplicate_element_ids

violations = find_duplicate_element_ids(document.pages)
for violation in violations:
    print(violation.to_dict())
```

The validator indexes text blocks, tables, images, drawings, links, annotations, and widgets. It reports every blank identity and every identity defined by more than one element. Evidence is deterministic and contains the element ID, each page and collection where it occurs, and the stable rule ID `document-element-id-uniqueness-v1`.

The function never mutates the artifact. Results are independent of page and element input order. This validation is additive and does not change the canonical artifact schema.

## Why this is required

A relationship target such as `target_id="table-12"` is only trustworthy when it resolves to exactly one artifact element. Duplicate IDs make graph traversal ambiguous even when every target string exists. Run identity validation before relationship integrity validation when accepting externally produced or manually modified artifacts.
