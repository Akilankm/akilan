# Image-heavy benchmark fixture

AKILAN's generated CI corpus includes `image_heavy.pdf`, a deterministic and copyright-free fixture for embedded-image and occurrence-level extraction behavior.

## Contract

The single-page fixture contains three raster-image occurrences:

1. a generated rectangular RGB image;
2. a rotated reuse of the same embedded image object at a different rectangle;
3. a distinct generated square RGB image.

The pixels are created locally through PyMuPDF. No downloaded media, Pillow, external encoder, or additional runtime dependency is used.

## Evidence

The generated corpus report records two related counts for every page:

- `image_occurrence_count`: the number of positioned image occurrences returned by `Page.get_image_info(xrefs=True)`;
- `embedded_image_count`: the number of distinct positive image xrefs referenced by those occurrences.

For `image_heavy.pdf`, the expected values are:

```json
{
  "image_occurrence_count": 3,
  "embedded_image_count": 2
}
```

The distinction is intentional. A reusable embedded image can occur multiple times with different rectangles or transforms, and the benchmark must preserve both asset identity and occurrence geometry.

## Regression expectations

Focused tests verify that:

- all three image occurrences survive save and reopen;
- the first two occurrences share one xref;
- the third occurrence uses a different xref;
- reused occurrences retain distinct bounding boxes;
- deterministic captions remain available as text evidence;
- corpus ordering and machine-readable evidence remain stable.

The fixture extends benchmark coverage only. It does not alter the canonical artifact schema or production extraction heuristics.
