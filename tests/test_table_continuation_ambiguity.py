from __future__ import annotations

from akilan.geometry import BBox
from akilan.models import PageArtifact, TableElement
from akilan.table_relationships import infer_table_continuations


def _table(element_id: str, bbox: BBox) -> TableElement:
    return TableElement(
        id=element_id,
        bbox=bbox,
        row_count=2,
        column_count=2,
        rows=[["Product", "Value"], ["A", "1"]],
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


def test_ambiguous_continuation_candidates_are_not_linked() -> None:
    source = _table("source", BBox(50.0, 620.0, 550.0, 790.0))
    first = _table("candidate-a", BBox(50.0, 8.0, 550.0, 190.0))
    second = _table("candidate-b", BBox(50.0, 12.0, 550.0, 194.0))
    pages = [_page(0, [source]), _page(1, [second, first])]

    relationships = infer_table_continuations(pages)

    assert relationships == []
    assert "table_continuations" not in pages[0].metrics
    assert pages[0].metrics["table_continuation_ambiguities"] == [
        {
            "source_table_id": "source",
            "candidate_table_ids": ["candidate-a", "candidate-b"],
            "rule_id": "table-continuation-candidate-margin-v1",
            "confidence_margin": 0.0,
            "minimum_margin": 0.08,
        }
    ]
    assert pages[1].metrics["table_continuation_ambiguities"] == pages[0].metrics[
        "table_continuation_ambiguities"
    ]


def test_ambiguity_diagnostics_are_idempotent_and_order_independent() -> None:
    source = _table("source", BBox(50.0, 620.0, 550.0, 790.0))
    candidates = [
        _table("candidate-a", BBox(50.0, 8.0, 550.0, 190.0)),
        _table("candidate-b", BBox(50.0, 12.0, 550.0, 194.0)),
    ]
    pages = [_page(0, [source]), _page(1, list(reversed(candidates)))]

    infer_table_continuations(pages)
    first = [dict(item) for item in pages[0].metrics["table_continuation_ambiguities"]]
    pages[1].tables = candidates
    infer_table_continuations(pages)

    assert pages[0].metrics["table_continuation_ambiguities"] == first
