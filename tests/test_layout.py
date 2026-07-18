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


def _order(elements: list[TableElement]) -> list[str]:
    return [
        item.element_id
        for item in build_reading_order(
            page_width=600,
            text_blocks=[],
            tables=elements,
            images=[],
            drawings=[],
            suppress_table_text=True,
        )
    ]


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


def test_overlapping_column_items_are_not_stranded_after_later_spans() -> None:
    elements = [
        _table("left-overlap", 40, 80, 260, 150),
        _table("right-overlap", 340, 80, 560, 150),
        _table("first-span", 20, 100, 580, 120),
        _table("left-middle", 40, 160, 260, 200),
        _table("right-middle", 340, 160, 560, 200),
        _table("second-span", 20, 220, 580, 250),
        _table("left-bottom", 40, 280, 260, 320),
        _table("right-bottom", 340, 280, 560, 320),
    ]

    assert _order(elements) == [
        "first-span",
        "left-overlap",
        "left-middle",
        "right-overlap",
        "right-middle",
        "second-span",
        "left-bottom",
        "right-bottom",
    ]


def test_spanning_band_order_is_independent_of_input_sequence() -> None:
    elements = [
        _table("left-top", 40, 40, 260, 80),
        _table("right-top", 340, 40, 560, 80),
        _table("span", 20, 100, 580, 130),
        _table("left-bottom", 40, 160, 260, 200),
        _table("right-bottom", 340, 160, 560, 200),
    ]

    assert _order(elements) == _order(list(reversed(elements)))


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
    assert analysis.confidence == 0.75
    assert analysis.ambiguity_reasons == ("elements_near_column_separator",)


def test_layout_analysis_reports_population_imbalance() -> None:
    elements = [
        _table("left-1", 40, 40, 260, 80),
        _table("left-2", 40, 100, 260, 140),
        _table("left-3", 40, 160, 260, 200),
        _table("left-4", 40, 220, 260, 260),
        _table("left-5", 40, 280, 260, 320),
        _table("right-1", 340, 40, 560, 80),
        _table("right-2", 340, 100, 560, 140),
    ]

    analysis = analyze_layout(page_width=600, elements=elements)

    assert analysis.column_count == 2
    assert analysis.column_element_counts == (5, 2)
    assert analysis.confidence == 0.8929
    assert analysis.ambiguity_reasons == ("strong_column_population_imbalance",)


def test_empty_layout_has_complete_confidence() -> None:
    analysis = analyze_layout(page_width=600, elements=[])

    assert analysis.confidence == 1.0
    assert analysis.ambiguity_reasons == ()


def test_layout_analysis_is_deterministic_for_identical_geometry() -> None:
    elements = [
        _table("left-1", 40, 40, 260, 80),
        _table("right-1", 340, 40, 560, 80),
        _table("left-2", 40, 100, 260, 140),
        _table("right-2", 340, 100, 560, 140),
    ]

    first = analyze_layout(page_width=600, elements=elements)
    second = analyze_layout(page_width=600, elements=list(reversed(elements)))

    assert first == second
