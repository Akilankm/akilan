from __future__ import annotations

from akilan.geometry import BBox
from akilan.models import PageArtifact, TableElement
from akilan.projection import page_metrics
from akilan.table_relationships import infer_table_continuations


def _table(
    element_id: str,
    bbox: BBox,
    rows: list[list[str | None]],
) -> TableElement:
    return TableElement(
        id=element_id,
        bbox=bbox,
        row_count=len(rows),
        column_count=max((len(row) for row in rows), default=0),
        rows=rows,
        cells=[],
        markdown="",
    )


def _page(index: int, tables: list[TableElement]) -> PageArtifact:
    return PageArtifact(
        page_index=index,
        page_number=index + 1,
        label=str(index + 1),
        width=600.0,
        height=800.0,
        rotation=0,
        mediabox=BBox(0.0, 0.0, 600.0, 800.0),
        cropbox=BBox(0.0, 0.0, 600.0, 800.0),
        tables=tables,
    )


def test_infers_adjacent_page_continuation_with_repeated_header() -> None:
    first = _table(
        "p0001_table_000",
        BBox(50.0, 610.0, 550.0, 790.0),
        [["Product", "Value"], ["A", "1"]],
    )
    second = _table(
        "p0002_table_000",
        BBox(52.0, 10.0, 548.0, 210.0),
        [["Product", "Value"], ["B", "2"]],
    )
    pages = [_page(0, [first]), _page(1, [second])]

    relationships = infer_table_continuations(pages)

    assert len(relationships) == 1
    relationship = relationships[0]
    assert relationship.source_table_id == first.id
    assert relationship.target_table_id == second.id
    assert relationship.repeated_header is True
    assert relationship.confidence == 0.99
    assert pages[0].metrics["table_continuations"] == pages[1].metrics["table_continuations"]
    assert page_metrics(pages[0])["table_continuations"][0]["rule_id"] == "adjacent-page-table-continuation-v1"


def test_rejects_mismatched_columns_and_weak_alignment() -> None:
    first = _table("first", BBox(50.0, 650.0, 300.0, 790.0), [["A", "B"]])
    wrong_columns = _table("wrong-columns", BBox(50.0, 10.0, 300.0, 180.0), [["A", "B", "C"]])
    weak_alignment = _table("weak-alignment", BBox(400.0, 10.0, 590.0, 180.0), [["A", "B"]])

    assert infer_table_continuations([_page(0, [first]), _page(1, [wrong_columns, weak_alignment])]) == []


def test_inference_is_deterministic_idempotent_and_one_to_one() -> None:
    left_a = _table("left-a", BBox(40.0, 630.0, 280.0, 790.0), [["A", "B"]])
    left_b = _table("left-b", BBox(320.0, 630.0, 560.0, 790.0), [["C", "D"]])
    right_a = _table("right-a", BBox(42.0, 5.0, 278.0, 180.0), [["A", "B"]])
    right_b = _table("right-b", BBox(322.0, 5.0, 558.0, 180.0), [["C", "D"]])
    pages = [_page(0, [left_b, left_a]), _page(1, [right_b, right_a])]

    first = infer_table_continuations(pages)
    first_metrics = [dict(page.metrics) for page in pages]
    second = infer_table_continuations(pages)

    assert first == second
    assert [page.metrics for page in pages] == first_metrics
    assert [(item.source_table_id, item.target_table_id) for item in first] == [
        ("left-a", "right-a"),
        ("left-b", "right-b"),
    ]
