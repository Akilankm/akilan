from __future__ import annotations

from copy import deepcopy

from akilan import find_persisted_graph_violations


def _document() -> dict[str, object]:
    return {
        "pages": [
            {
                "page_index": 0,
                "text_blocks": [
                    {
                        "id": "caption-1",
                        "relationships": {"describes": ["table-1"]},
                    }
                ],
                "tables": [{"id": "table-1", "relationships": {}}],
                "images": [],
                "drawings": [],
                "links": [],
                "annotations": [],
                "widgets": [],
            }
        ]
    }


def test_valid_cross_collection_relationship_passes() -> None:
    document = _document()

    assert find_persisted_graph_violations(document) == []


def test_reports_duplicate_blank_self_duplicate_and_dangling_targets() -> None:
    document = _document()
    page = document["pages"][0]
    page["images"] = [{"id": "table-1", "relationships": {}}]
    page["drawings"] = [{"id": "", "relationships": {}}]
    page["text_blocks"][0]["relationships"] = {
        "": ["caption-1", "missing", "missing", ""],
    }

    violations = find_persisted_graph_violations(document)

    assert [item.rule_id for item in violations].count(
        "document-element-id-uniqueness-v1"
    ) == 3
    assert [item.rule_id for item in violations].count(
        "relationship-target-integrity-v1"
    ) == 6
    assert any("does not exist" in item.message for item in violations)
    assert any("must not reference" in item.message for item in violations)
    assert any("duplicate relationship target" in item.message for item in violations)


def test_results_are_deterministic_and_input_is_not_mutated() -> None:
    first = _document()
    first["pages"][0]["text_blocks"][0]["relationships"] = {
        "describes": ["missing-b", "missing-a"]
    }
    second = deepcopy(first)
    second["pages"][0]["text_blocks"][0]["relationships"]["describes"].reverse()
    before = deepcopy(first)

    first_result = [item.to_dict() for item in find_persisted_graph_violations(first)]
    second_result = [item.to_dict() for item in find_persisted_graph_violations(second)]

    assert first == before
    assert sorted(item["message"] for item in first_result) == sorted(
        item["message"] for item in second_result
    )


def test_defensive_handling_of_non_mapping_pages_and_collections() -> None:
    document = {
        "pages": [None, {"page_index": 1, "text_blocks": "invalid"}],
    }

    assert find_persisted_graph_violations(document) == []
