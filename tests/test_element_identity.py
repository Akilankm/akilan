from __future__ import annotations

from akilan.element_identity import find_duplicate_element_ids
from akilan.geometry import BBox
from akilan.models import PageArtifact, TextBlock


def _block(block_id: str) -> TextBlock:
    return TextBlock(
        id=block_id,
        bbox=BBox(0.0, 0.0, 10.0, 10.0),
        text=block_id,
        lines=[],
        source_block_number=None,
    )


def _page(page_index: int, blocks: list[TextBlock]) -> PageArtifact:
    box = BBox(0.0, 0.0, 100.0, 100.0)
    return PageArtifact(
        page_index=page_index,
        page_number=page_index + 1,
        label=str(page_index + 1),
        width=100.0,
        height=100.0,
        rotation=0,
        mediabox=box,
        cropbox=box,
        text_blocks=blocks,
    )


def test_unique_document_element_ids_have_no_violations() -> None:
    pages = [_page(0, [_block("alpha")]), _page(1, [_block("beta")])]

    assert find_duplicate_element_ids(pages) == []


def test_reports_duplicate_ids_with_all_stable_occurrences() -> None:
    violations = find_duplicate_element_ids(
        [
            _page(1, [_block("shared")]),
            _page(0, [_block("shared"), _block("shared")]),
        ]
    )

    assert [item.to_dict() for item in violations] == [
        {
            "element_id": "shared",
            "occurrences": [
                {"page_index": 0, "collection": "text_blocks"},
                {"page_index": 0, "collection": "text_blocks"},
                {"page_index": 1, "collection": "text_blocks"},
            ],
            "rule_id": "document-element-id-uniqueness-v1",
        }
    ]


def test_reports_blank_element_ids() -> None:
    violations = find_duplicate_element_ids([_page(0, [_block("")])])

    assert violations[0].to_dict() == {
        "element_id": "",
        "occurrences": [{"page_index": 0, "collection": "text_blocks"}],
        "rule_id": "document-element-id-uniqueness-v1",
    }


def test_results_are_independent_of_page_and_element_order() -> None:
    forward = find_duplicate_element_ids(
        [_page(1, [_block("z"), _block("a")]), _page(0, [_block("z"), _block("a")])]
    )
    reverse = find_duplicate_element_ids(
        [_page(0, [_block("a"), _block("z")]), _page(1, [_block("a"), _block("z")])]
    )

    assert [item.to_dict() for item in forward] == [item.to_dict() for item in reverse]
