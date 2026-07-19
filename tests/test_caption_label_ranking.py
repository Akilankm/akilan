from __future__ import annotations

from akilan.geometry import BBox
from akilan.models import ImageElement, PageArtifact, ReadingOrderItem, TableElement, TextBlock
from akilan.relationships import infer_document_relationships


def _caption(text: str) -> TextBlock:
    return TextBlock(
        id="caption",
        bbox=BBox(80, 320, 330, 340),
        text=text,
        lines=[],
        source_block_number=None,
        semantic_role="caption",
        semantic_confidence=1.0,
    )


def _page(caption: TextBlock) -> PageArtifact:
    return PageArtifact(
        page_index=0,
        page_number=1,
        label="1",
        width=595.0,
        height=842.0,
        rotation=0,
        mediabox=BBox(0, 0, 595, 842),
        cropbox=BBox(0, 0, 595, 842),
        text_blocks=[caption],
        reading_order=[ReadingOrderItem(0, "text", caption.id, caption.bbox)],
    )


def _table(element_id: str, bbox: BBox) -> TableElement:
    return TableElement(
        id=element_id,
        bbox=bbox,
        row_count=1,
        column_count=1,
        rows=[["value"]],
        cells=[[bbox.x0, bbox.y0, bbox.x1, bbox.y1]],
        markdown="| value |",
    )


def _image(element_id: str, bbox: BBox) -> ImageElement:
    return ImageElement(
        id=element_id,
        bbox=bbox,
        xref=1,
        occurrence=0,
        pixel_width=100,
        pixel_height=100,
        colorspace=3,
        bits_per_component=8,
        extension="png",
        asset_path=None,
        digest_sha256=None,
    )


def test_table_caption_rejects_stronger_image_candidate() -> None:
    caption = _caption("Table 4. Accuracy by model")
    page = _page(caption)
    page.images = [_image("closer-image", BBox(75, 230, 335, 315))]
    page.tables = [_table("matching-table", BBox(70, 190, 340, 295))]

    infer_document_relationships([page])

    assert caption.relationships["describes"] == ["matching-table"]
    evidence = next(
        item for item in page.metrics["relationship_evidence"]
        if item["relationship"] == "describes"
    )
    assert evidence["target_id"] == "matching-table"


def test_explicit_table_caption_abstains_without_compatible_visual() -> None:
    caption = _caption("TABLE II Results")
    page = _page(caption)
    page.images = [_image("only-image", BBox(75, 230, 335, 315))]

    infer_document_relationships([page])

    assert "describes" not in caption.relationships
    assert page.metrics["relationship_ambiguities"] == [
        {
            "source_id": "caption",
            "relationship": "describes",
            "rule_id": "caption-explicit-type-gate-v1",
            "candidate_ids": ["only-image"],
            "expected_visual_type": "table",
        }
    ]


def test_unlabelled_caption_preserves_geometry_first_ranking() -> None:
    caption = _caption("Accuracy by model")
    page = _page(caption)
    page.images = [_image("closer-image", BBox(75, 230, 335, 315))]
    page.tables = [_table("farther-table", BBox(70, 180, 340, 255))]

    infer_document_relationships([page])

    assert caption.relationships["describes"] == ["closer-image"]
