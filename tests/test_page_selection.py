from __future__ import annotations

import pytest

from akilan import PageSelectionError, parse_page_selection


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1", (1,)),
        ("1,3-5,9", (1, 3, 4, 5, 9)),
        (" 1 , 3 - 4 ", (1, 3, 4)),
        ("10-12", (10, 11, 12)),
    ],
)
def test_parse_page_selection_accepts_canonical_expressions(
    expression: str,
    expected: tuple[int, ...],
) -> None:
    assert parse_page_selection(expression) == expected


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("", "must not be empty"),
        ("1,,2", "token 2 is empty"),
        ("0", "positive one-based"),
        ("-1", "incomplete range"),
        ("3-1", "descending range"),
        ("1,1", "duplicate page 1"),
        ("1-3,3", "duplicate page 3"),
        ("2,1", "ascending source order"),
        ("1-2-3", "at most one range separator"),
        ("one", "non-integer page"),
        ("１", "non-integer page"),
    ],
)
def test_parse_page_selection_rejects_ambiguous_or_invalid_input(
    expression: str,
    message: str,
) -> None:
    with pytest.raises(PageSelectionError, match=message):
        parse_page_selection(expression)


def test_parse_page_selection_rejects_non_string_input() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        parse_page_selection(1)  # type: ignore[arg-type]
