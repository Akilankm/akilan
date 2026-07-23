from __future__ import annotations

from akilan import DuplicateFootnoteMarker, find_duplicate_footnote_markers
from akilan.geometry import BBox
from akilan.models import PageArtifact, TextBlock


def _block(element_id: str, role: str, text: str) -> TextBlock:
    return TextBlock(
        id=element_id,
        bbox=BBox(50.0, 700.0, 500.0, 730.0),
        text=text,
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
    )


def test_duplicate_footnote_markers_are_reported_deterministically() -> None:
    page = _page(
        1,
        [
            _block("footnote-b", "footnote", "[1] Second definition."),
            _block("paragraph", "paragraph", "[1] This is not a definition."),
            _block("footnote-a", "footnote", "[1] First definition."),
        ],
    )

    conflicts = find_duplicate_footnote_markers([page])

    assert conflicts == [
        DuplicateFootnoteMarker(
            page_index=1,
            marker="[1]",
            definition_ids=("footnote-a", "footnote-b"),
        )
    ]
    assert conflicts[0].to_dict() == {
        "page_index": 1,
        "marker": "[1]",
        "definition_ids": ["footnote-a", "footnote-b"],
        "rule_id": "duplicate-footnote-definition-marker-v1",
    }


def test_validation_ignores_unique_and_unsupported_definitions() -> None:
    page = _page(
        0,
        [
            _block("footnote-1", "footnote", "[1] Supported definition."),
            _block("footnote-2", "footnote", "2. Unsupported definition."),
            _block("caption", "caption", "[1] Not classified as a footnote."),
        ],
    )

    assert find_duplicate_footnote_markers([page]) == []


def test_validation_is_page_local_and_input_order_independent() -> None:
    first = _page(0, [_block("p0-footnote", "footnote", "[a] First page.")])
    second = _page(
        1,
        [
            _block("z-definition", "footnote", "[A] Uppercase marker."),
            _block("a-definition", "footnote", "[a] Lowercase marker."),
        ],
    )

    forward = find_duplicate_footnote_markers([first, second])
    reverse = find_duplicate_footnote_markers([second, first])

    assert reverse == forward
    assert forward == [
        DuplicateFootnoteMarker(
            page_index=1,
            marker="[a]",
            definition_ids=("a-definition", "z-definition"),
        )
    ]
