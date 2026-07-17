from __future__ import annotations

from akilan.geometry import BBox
from akilan.models import PageArtifact, ReadingOrderItem, TableElement, TextBlock
from akilan.relationships import infer_document_relationships


def _block(
    element_id: str,
    role: str,
    y0: float,
    y1: float,
    *,
    x0: float = 50.0,
    x1: float = 500.0,
) -> TextBlock:
    return TextBlock(
        id=element_id,
        bbox=BBox(x0, y0, x1, y1),
        text=element_id,
        lines=[],
        source_block_number=None,
        semantic_role=role,  # type: ignore[arg-type]
        semantic_confidence=1.0,
    )


def _page(index: int, blocks: list[TextBlock]) -> PageArtifact:
    return PageArtifact(
        page_index=index,
        page_number=index + 1,
        label=str(index + 1),
        width=595.0,
        height=842.0,
        rotation=0,
        mediabox=BBox(0.0, 0.0, 595.0, 842.0),
        cropbox=BBox(0.0, 0.0, 595.0, 842.0),
        text_blocks=blocks,
        reading_order=[
            ReadingOrderItem(
                order=order,
                element_type="text",
                element_id=block.id,
                bbox=block.bbox,
            )
            for order, block in enumerate(blocks)
        ],
    )


def test_relationships_preserve_cross_page_section_context() -> None:
    title = _block("title", "document_title", 40, 70)
    heading = _block("heading", "heading_1", 100, 125)
    first_body = _block("first-body", "paragraph", 140, 190)
    second_body = _block("second-body", "paragraph", 80, 130)
    subsection = _block("subsection", "heading_2", 150, 175)
    nested_body = _block("nested-body", "paragraph", 190, 240)

    pages = [
        _page(0, [title, heading, first_body]),
        _page(1, [second_body, subsection, nested_body]),
    ]

    infer_document_relationships(pages)

    assert heading.relationships["parent_heading"] == ["title"]
    assert first_body.relationships["section_heading"] == ["heading"]
    assert second_body.relationships["section_heading"] == ["heading"]
    assert subsection.relationships["parent_heading"] == ["heading"]
    assert nested_body.relationships["section_heading"] == ["subsection"]
    assert heading.relationships["contains"] == ["first-body", "second-body", "subsection"]


def test_caption_links_only_to_nearby_overlapping_visual() -> None:
    heading = _block("heading", "heading_1", 60, 90)
    caption = _block("caption", "caption", 320, 340, x0=80, x1=330)
    page = _page(0, [heading, caption])
    page.tables = [
        TableElement(
            id="near-table",
            bbox=BBox(70, 200, 340, 310),
            row_count=1,
            column_count=1,
            rows=[["value"]],
            cells=[[70.0, 200.0, 340.0, 310.0]],
            markdown="| value |",
        ),
        TableElement(
            id="far-table",
            bbox=BBox(400, 200, 560, 310),
            row_count=1,
            column_count=1,
            rows=[["other"]],
            cells=[[400.0, 200.0, 560.0, 310.0]],
            markdown="| other |",
        ),
    ]

    infer_document_relationships([page])

    assert caption.relationships["describes"] == ["near-table"]
    assert caption.relationships["section_heading"] == ["heading"]


def test_relationship_inference_is_idempotent_and_preserves_external_edges() -> None:
    heading = _block("heading", "heading_1", 60, 90)
    body = _block("body", "paragraph", 110, 160)
    body.relationships["external_reference"] = ["annotation-1"]
    page = _page(0, [heading, body])

    infer_document_relationships([page])
    first = dict(body.relationships)
    infer_document_relationships([page])

    assert body.relationships == first
    assert body.relationships["external_reference"] == ["annotation-1"]
    assert body.relationships["section_heading"] == ["heading"]
