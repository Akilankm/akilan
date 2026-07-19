from __future__ import annotations

from akilan.geometry import BBox
from akilan.models import PageArtifact, TextBlock
from akilan.relationship_integrity import find_relationship_integrity_violations


def _block(block_id: str, relationships: dict[str, list[str]] | None = None) -> TextBlock:
    return TextBlock(
        id=block_id,
        bbox=BBox(0.0, 0.0, 10.0, 10.0),
        text=block_id,
        lines=[],
        source_block_number=None,
        relationships=relationships or {},
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


def test_valid_cross_page_relationship_has_no_violations() -> None:
    pages = [
        _page(0, [_block("source", {"has_footnote": ["target"]})]),
        _page(1, [_block("target")]),
    ]

    assert find_relationship_integrity_violations(pages) == []


def test_reports_dangling_self_duplicate_and_empty_targets() -> None:
    source = _block(
        "source",
        {
            "has_footnote": ["missing", "source", "target", "target", ""],
        },
    )
    violations = find_relationship_integrity_violations(
        [_page(0, [source, _block("target")])]
    )

    assert [item.to_dict() for item in violations] == [
        {
            "page_index": 0,
            "source_id": "source",
            "relationship": "has_footnote",
            "target_id": "",
            "reason": "target ID must be non-empty",
            "rule_id": "relationship-target-integrity-v1",
        },
        {
            "page_index": 0,
            "source_id": "source",
            "relationship": "has_footnote",
            "target_id": "missing",
            "reason": "target ID does not exist in the document artifact",
            "rule_id": "relationship-target-integrity-v1",
        },
        {
            "page_index": 0,
            "source_id": "source",
            "relationship": "has_footnote",
            "target_id": "source",
            "reason": "self-referential relationship is not allowed",
            "rule_id": "relationship-target-integrity-v1",
        },
        {
            "page_index": 0,
            "source_id": "source",
            "relationship": "has_footnote",
            "target_id": "target",
            "reason": "duplicate relationship target",
            "rule_id": "relationship-target-integrity-v1",
        },
    ]


def test_reports_blank_relationship_name() -> None:
    violations = find_relationship_integrity_violations(
        [_page(0, [_block("source", {"   ": ["target"]}), _block("target")])]
    )

    assert violations[0].to_dict() == {
        "page_index": 0,
        "source_id": "source",
        "relationship": "   ",
        "target_id": "",
        "reason": "relationship name must be non-empty",
        "rule_id": "relationship-target-integrity-v1",
    }


def test_results_are_independent_of_page_block_and_target_order() -> None:
    first = _page(
        1,
        [_block("b", {"references": ["missing-z", "missing-a"]}), _block("a")],
    )
    second = _page(0, [_block("c", {"references": ["missing-b"]})])

    forward = find_relationship_integrity_violations([first, second])
    reverse = find_relationship_integrity_violations(
        [
            _page(0, list(reversed(second.text_blocks))),
            _page(
                1,
                [
                    _block("a"),
                    _block("b", {"references": ["missing-a", "missing-z"]}),
                ],
            ),
        ]
    )

    assert [item.to_dict() for item in forward] == [item.to_dict() for item in reverse]
