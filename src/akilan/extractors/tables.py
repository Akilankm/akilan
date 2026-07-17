"""Native PyMuPDF table extraction."""

from __future__ import annotations

import pymupdf

from ..geometry import BBox
from ..models import TableElement
from ..native import table_markdown


def extract_tables(page: pymupdf.Page, page_index: int) -> list[TableElement]:
    try:
        finder = page.find_tables()
    except Exception:
        return []
    result: list[TableElement] = []
    for index, table in enumerate(getattr(finder, "tables", [])):
        rows = [[None if cell is None else str(cell) for cell in row] for row in table.extract()]
        cells = [list(cell) if cell is not None else None for cell in getattr(table, "cells", [])]
        result.append(
            TableElement(
                id=f"p{page_index + 1:04d}_table_{index:03d}",
                bbox=BBox.from_value(table.bbox),
                row_count=int(getattr(table, "row_count", len(rows))),
                column_count=int(getattr(table, "col_count", max((len(row) for row in rows), default=0))),
                rows=rows,
                cells=cells,
                markdown=table_markdown(rows),
            )
        )
    return result
