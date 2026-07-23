"""Links, annotations, and form widget extraction."""

from __future__ import annotations

import pymupdf

from ..geometry import BBox
from ..models import AnnotationElement, LinkElement, WidgetElement
from ..serialization import to_jsonable


def extract_links(page: pymupdf.Page, page_index: int) -> list[LinkElement]:
    result: list[LinkElement] = []
    for index, link in enumerate(page.get_links()):
        target_point = to_jsonable(link.get("to")) if link.get("to") is not None else None
        result.append(
            LinkElement(
                id=f"p{page_index + 1:04d}_link_{index:03d}",
                bbox=BBox.from_value(link.get("from", (0, 0, 0, 0))),
                kind=int(link.get("kind") or 0),
                target_page=int(link["page"]) if link.get("page") is not None else None,
                target_point=target_point if isinstance(target_point, list) else None,
                uri=link.get("uri"),
                file=link.get("file"),
                xref=int(link["xref"]) if link.get("xref") is not None else None,
            )
        )
    return result


def extract_annotations(page: pymupdf.Page, page_index: int) -> list[AnnotationElement]:
    try:
        annotations = page.annots()
    except Exception:
        annotations = None
    if annotations is None:
        return []
    result: list[AnnotationElement] = []
    for index, annotation in enumerate(annotations):
        try:
            result.append(
                AnnotationElement(
                    id=f"p{page_index + 1:04d}_annot_{index:03d}",
                    bbox=BBox.from_value(annotation.rect),
                    xref=int(annotation.xref),
                    annotation_type=to_jsonable(annotation.type),
                    info=to_jsonable(annotation.info),
                    colors=to_jsonable(annotation.colors),
                    border=to_jsonable(annotation.border),
                    flags=int(annotation.flags),
                    opacity=float(annotation.opacity),
                )
            )
        except Exception:
            continue
    return result


def extract_widgets(page: pymupdf.Page, page_index: int) -> list[WidgetElement]:
    try:
        widgets = page.widgets()
    except Exception:
        widgets = None
    if widgets is None:
        return []
    return [
        WidgetElement(
            id=f"p{page_index + 1:04d}_widget_{index:03d}",
            bbox=BBox.from_value(widget.rect),
            xref=int(widget.xref),
            field_name=widget.field_name,
            field_label=widget.field_label,
            field_type=widget.field_type,
            field_type_string=widget.field_type_string,
            field_value=to_jsonable(widget.field_value),
            field_flags=widget.field_flags,
        )
        for index, widget in enumerate(widgets)
    ]
