from __future__ import annotations

from akilan.geometry import BBox
from akilan.models import PageArtifact, TableElement
from akilan.table_continuation import infer_table_continuations


def _table(element_id: str, y0: float, y1: float, *, header: str = "Name", width: float = 500.0) -> TableElement:
    return TableElement(
        id=element_id,
        bbox=BBox(50.0, y0, 50.0 + width, y1),
        row_count=2,
        column_count=2,
        rows=[[header, "Value"], ["A", "1"]],
        cells=[],
        markdown="| Name | Value |",
    )


def _page(index: int, tables: list[TableElement]) -> PageArtifact:
    return PageArtifact(
        page_index=index,
        page_number=index + 1,
        label=str(index + 1),
        width=595.0,
        height=842.0,
        rotation=0,
        mediabox=BBox(0.0, 0.0, 595.0, 842.0),
        cropbox=BBox(0.0, 0.0, 595.0, 842.0),
        tables=tables,
    )


def test_infers_adjacent_page_continuation_with_audit_evidence() -> None:
    first = _page(0, [_table("table-1", 620.0, 830.0)])
    second = _page(1, [_table("table-2", 20.0, 250.0)])

    infer_table_continuations([second, first])

    assert first.metrics["table_continuations"] == [
        {
            "source_table_id": "table-1",
            "target_table_id": "table-2",
            "relationship": "continues_on_next_page",
            "rule_id": "adjacent-page-table-continuation-v1",
            "confidence": 1.0,
            "signals": {
                "column_count_match": True,
                "header_similarity": 1.0,
                "width_similarity": 1.0,
            },
        }
    ]
    assert second.metrics["table_continuations"][0]["relationship"] == "continues_from_previous_page"


def test_abstains_when_geometry_or_structure_is_incompatible() -> None:
    first = _page(0, [_table("middle-table", 200.0, 400.0)])
    second_table = _table("top-table", 20.0, 250.0)
    second_table.column_count = 3
    second = _page(1, [second_table])

    infer_table_continuations([first, second])

    assert "table_continuations" not in first.metrics
    assert "table_continuations" not in second.metrics


def test_inference_is_idempotent_and_preserves_external_metrics() -> None:
    first = _page(0, [_table("table-1", 620.0, 830.0)])
    second = _page(1, [_table("table-2", 20.0, 250.0)])
    first.metrics["external"] = {"owner": "other-pass"}

    infer_table_continuations([first, second])
    evidence = [dict(first.metrics["table_continuations"][0])]
    infer_table_continuations([first, second])

    assert first.metrics["table_continuations"] == evidence
    assert first.metrics["external"] == {"owner": "other-pass"}


def test_abstains_when_two_candidates_are_effectively_tied() -> None:
    first = _page(0, [_table("table-1", 620.0, 830.0)])
    second = _page(
        1,
        [
            _table("table-2a", 20.0, 220.0),
            _table("table-2b", 25.0, 225.0),
        ],
    )

    infer_table_continuations([first, second])

    assert "table_continuations" not in first.metrics
    assert "table_continuations" not in second.metrics
