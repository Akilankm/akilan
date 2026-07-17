"""Vector drawing extraction."""

from __future__ import annotations

import pymupdf

from ..geometry import BBox
from ..models import DrawingElement
from ..serialization import to_jsonable


def extract_drawings(page: pymupdf.Page, page_index: int, min_area: float) -> list[DrawingElement]:
    try:
        drawings = page.get_drawings(extended=True)
    except TypeError:
        drawings = page.get_drawings()
    except Exception:
        return []
    result: list[DrawingElement] = []
    for index, drawing in enumerate(drawings):
        rect = drawing.get("rect")
        if rect is None:
            continue
        bbox = BBox.from_value(rect)
        if bbox.area < min_area and bbox.width < 1.0 and bbox.height < 1.0:
            continue
        opacity = drawing.get("fill_opacity")
        if opacity is None:
            opacity = drawing.get("stroke_opacity")
        result.append(
            DrawingElement(
                id=f"p{page_index + 1:04d}_drawing_{index:04d}",
                bbox=bbox,
                drawing_type=drawing.get("type"),
                fill=to_jsonable(drawing.get("fill")),
                color=to_jsonable(drawing.get("color")),
                width=float(drawing["width"]) if drawing.get("width") is not None else None,
                opacity=float(opacity) if opacity is not None else 1.0,
                close_path=drawing.get("closePath"),
                layer=drawing.get("layer"),
                sequence_number=drawing.get("seqno"),
                items=to_jsonable(drawing.get("items", [])),
            )
        )
    return result
