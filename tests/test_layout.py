from __future__ import annotations

from akilan.geometry import BBox
from akilan.layout import analyze_layout, build_reading_order
from akilan.models import TableElement


def _table(element_id: str, x0: float, y0: float, x1: float, y1: float) -> TableElement:
    return TableElement(
        id=element_id,
        bbox=BBox(x0, y0, x1, y1),
        row_count=1,
        column_count=1,
        rows=[[element_id]],
        cells=[],
        markdown=f"| {element_id} |",
    )


def test_cross_column_object_is_spanning_and_ordered_between_bands() -> None:
    elements = [
        _table("left-top", 40, 40, 260, 80),
        _table("right-top", 340, 40, 560, 80),
        _table("cross-column", 250, 100, 350, 140),
        _table("left-bottom", 40, 160, 260, 200),
        _table("right-bottom", 340, 160, 560, 200),
    ]

    analysis = analyze_layout(page_width=600, elements=elements)

    assert analysis.column_count == 2
    assert analysis.spanning_element_ids == ("cross-column",)
    assert analysis.column_element_counts == (2, 2)

    order = build_reading_order(
        page_width=600,
        text_blocks=[],
        tables=elements,
        images=[],
        drawings=[],
        suppress_table_text=True,
    )

    assert [item.element_id for item in order] == [
        "left-top",
        "right-top",
        "cross-column",
        "left-bottom",
        "right-bottom",
    ]
    assert [item.column_index for item in order] == [0, 1, None, 0, 1]


def test_layout_analysis_reports_weak_separator_assignments() -> None:
    elements = [
        _table("left-top", 40, 40, 260, 80),
        _table("right-top", 340, 40, 560, 80),
        _table("left-bottom", 40, 100, 260, 140),
        _table("right-bottom", 340, 100, 560, 140),
        _table("weak-boundary", 288, 160, 306, 190),
    ]

    analysis = analyze_layout(page_width=600, elements=elements)

    assert analysis.column_count == 2
    assert "weak-boundary" in analysis.ambiguous_element_ids
    assert sum(analysis.column_element_counts) == len(elements)


def test_layout_analysis_is_deterministic_for_identical_geometry() -> None:
    elements = [
        _table("left-1", 40, 40, 260, 80),
        _table("right-1", 340, 40, 560, 80),
        _table("left-2", 40, 100, 260, 140),
        _table("right-2", 340, 100, 560, 140),
    ]

    first = analyze_layout(page_width=600, elements=elements)
    second = analyze_layout(page_width=600, elements=list(reversed(elements)))

    assert first.column_boundaries == second.column_boundaries
    assert first.column_count == second.column_count
    assert first.column_element_counts == second.column_element_counts
