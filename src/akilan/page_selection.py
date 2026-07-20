"""Parse deterministic one-based PDF page selections."""

from __future__ import annotations


class PageSelectionError(ValueError):
    """Raised when a page-selection expression is malformed or ambiguous."""


def parse_page_selection(expression: str) -> tuple[int, ...]:
    """Parse a comma-separated one-based page/range expression.

    Examples:
        ``"1"`` -> ``(1,)``
        ``"1,3-5,9"`` -> ``(1, 3, 4, 5, 9)``

    The returned tuple is strictly ascending and duplicate-free so it can be
    passed directly to :class:`akilan.ExtractionConfig`. Overlapping ranges,
    duplicate pages, descending ranges, zero, negative values, and whitespace-
    only expressions are rejected rather than silently normalized.
    """

    if not isinstance(expression, str):
        raise TypeError("page selection must be a string")

    value = expression.strip()
    if not value:
        raise PageSelectionError("page selection must not be empty")

    pages: list[int] = []
    seen: set[int] = set()

    for index, raw_token in enumerate(value.split(","), start=1):
        token = raw_token.strip()
        if not token:
            raise PageSelectionError(f"page selection token {index} is empty")

        if "-" in token:
            if token.count("-") != 1:
                raise PageSelectionError(
                    f"page selection token {index} must contain at most one range separator"
                )
            start_text, end_text = (part.strip() for part in token.split("-", 1))
            if not start_text or not end_text:
                raise PageSelectionError(
                    f"page selection token {index} has an incomplete range"
                )
            start = _parse_positive_page(start_text, index)
            end = _parse_positive_page(end_text, index)
            if end < start:
                raise PageSelectionError(
                    f"page selection token {index} has a descending range: {token!r}"
                )
            token_pages = range(start, end + 1)
        else:
            token_pages = (_parse_positive_page(token, index),)

        for page in token_pages:
            if page in seen:
                raise PageSelectionError(
                    f"page selection contains duplicate page {page}"
                )
            seen.add(page)
            pages.append(page)

    if pages != sorted(pages):
        raise PageSelectionError("page selection must be in ascending source order")

    return tuple(pages)


def _parse_positive_page(value: str, token_index: int) -> int:
    if not value.isascii() or not value.isdecimal():
        raise PageSelectionError(
            f"page selection token {token_index} contains a non-integer page: {value!r}"
        )
    page = int(value)
    if page < 1:
        raise PageSelectionError(
            f"page selection token {token_index} must use positive one-based pages"
        )
    return page
