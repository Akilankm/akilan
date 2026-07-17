"""Text hierarchy extraction from PyMuPDF raw dictionaries."""

from __future__ import annotations

from typing import Any

import pymupdf

from ..geometry import BBox
from ..models import Character, TextBlock, TextLine, TextSpan
from ..native import point, span_text, text_flags


def extract_text_blocks(
    page: pymupdf.Page,
    page_index: int,
    include_characters: bool,
) -> tuple[list[TextBlock], list[dict[str, Any]]]:
    raw = page.get_text("rawdict", flags=text_flags(), sort=False)
    blocks: list[TextBlock] = []
    image_blocks: list[dict[str, Any]] = []
    for block_index, raw_block in enumerate(raw.get("blocks", [])):
        if raw_block.get("type") == 1:
            image_blocks.append(raw_block)
            continue
        if raw_block.get("type") != 0:
            continue
        lines: list[TextLine] = []
        block_text_parts: list[str] = []
        for line_index, raw_line in enumerate(raw_block.get("lines", [])):
            spans: list[TextSpan] = []
            line_text_parts: list[str] = []
            for span_index, raw_span in enumerate(raw_line.get("spans", [])):
                text = span_text(raw_span)
                characters: list[Character] = []
                if include_characters:
                    for raw_char in raw_span.get("chars", []):
                        characters.append(
                            Character(
                                text=str(raw_char.get("c") or ""),
                                bbox=BBox.from_value(raw_char.get("bbox", (0, 0, 0, 0))),
                                origin=point(raw_char.get("origin")),
                                synthetic=raw_char.get("synthetic"),
                            )
                        )
                spans.append(
                    TextSpan(
                        id=f"p{page_index + 1:04d}_b{block_index:04d}_l{line_index:03d}_s{span_index:03d}",
                        text=text,
                        bbox=BBox.from_value(raw_span.get("bbox", (0, 0, 0, 0))),
                        font=str(raw_span.get("font") or ""),
                        size=float(raw_span.get("size") or 0.0),
                        color=raw_span.get("color"),
                        alpha=raw_span.get("alpha"),
                        flags=int(raw_span.get("flags") or 0),
                        ascender=float(raw_span["ascender"]) if raw_span.get("ascender") is not None else None,
                        descender=float(raw_span["descender"]) if raw_span.get("descender") is not None else None,
                        origin=point(raw_span.get("origin")),
                        characters=characters,
                    )
                )
                line_text_parts.append(text)
            line_text = "".join(line_text_parts)
            lines.append(
                TextLine(
                    id=f"p{page_index + 1:04d}_b{block_index:04d}_l{line_index:03d}",
                    bbox=BBox.from_value(raw_line.get("bbox", raw_block.get("bbox", (0, 0, 0, 0)))),
                    text=line_text,
                    direction=tuple(float(value) for value in raw_line.get("dir", (1.0, 0.0))),  # type: ignore[arg-type]
                    writing_mode=int(raw_line.get("wmode") or 0),
                    spans=spans,
                )
            )
            block_text_parts.append(line_text)
        blocks.append(
            TextBlock(
                id=f"p{page_index + 1:04d}_text_{block_index:04d}",
                bbox=BBox.from_value(raw_block.get("bbox", (0, 0, 0, 0))),
                text="\n".join(part for part in block_text_parts if part),
                lines=lines,
                source_block_number=raw_block.get("number"),
            )
        )
    return blocks, image_blocks
