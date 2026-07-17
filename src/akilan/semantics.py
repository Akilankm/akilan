"""Typography- and geometry-based semantic role inference."""

from __future__ import annotations

import re
from collections import Counter
from statistics import median

from .models import PageArtifact, TextBlock
from .relationships import infer_document_relationships
from .table_relationships import infer_table_continuations

_LIST_PATTERN = re.compile(r"^\s*(?:[-•‣▪◦*]|\(?\d+[.)]|\(?[A-Za-z][.)])\s+")
_PAGE_NUMBER_PATTERN = re.compile(r"^\s*(?:page\s*)?\d+(?:\s*(?:of|/)\s*\d+)?\s*$", re.IGNORECASE)


def _is_bold(block: TextBlock) -> bool:
    return any("bold" in name.casefold() or "black" in name.casefold() for name in block.font_names)


def _is_monospace(block: TextBlock) -> bool:
    markers = ("mono", "courier", "consolas", "menlo", "code")
    return any(any(marker in name.casefold() for marker in markers) for name in block.font_names)


def _body_font_size(page: PageArtifact) -> float:
    sizes: list[float] = []
    for block in page.text_blocks:
        sizes.extend(
            span.size
            for line in block.lines
            for span in line.spans
            for _ in range(max(1, min(20, len(span.text.strip()))))
            if span.size > 0
        )
    return median(sizes) if sizes else 10.0


def assign_page_semantics(page: PageArtifact, header_ratio: float, footer_ratio: float) -> None:
    body_size = _body_font_size(page)
    top_limit = page.height * header_ratio
    bottom_limit = page.height * (1.0 - footer_ratio)

    for block in page.text_blocks:
        text = " ".join(block.text.split())
        size = block.dominant_font_size or body_size
        role = "paragraph"
        confidence = 0.55

        if not text:
            role, confidence = "unknown", 0.1
        elif block.bbox.y1 <= top_limit:
            role, confidence = "header", 0.78
        elif block.bbox.y0 >= bottom_limit:
            if _PAGE_NUMBER_PATTERN.match(text):
                role, confidence = "page_number", 0.95
            elif size <= body_size * 0.82:
                role, confidence = "footnote", 0.72
            else:
                role, confidence = "footer", 0.78
        elif _LIST_PATTERN.match(text):
            role, confidence = "list_item", 0.92
        elif _is_monospace(block):
            role, confidence = "code", 0.86
        elif page.page_index == 0 and size >= body_size * 1.65 and block.bbox.y0 < page.height * 0.35:
            role, confidence = "document_title", 0.9
        elif size >= body_size * 1.55:
            role, confidence = "heading_1", 0.88
        elif size >= body_size * 1.28 or (size >= body_size * 1.15 and _is_bold(block)):
            role, confidence = "heading_2", 0.82
        elif size >= body_size * 1.10 and _is_bold(block):
            role, confidence = "heading_3", 0.75
        elif size <= body_size * 0.78 and len(text) < 240:
            role, confidence = "caption", 0.6

        block.semantic_role = role  # type: ignore[assignment]
        block.semantic_confidence = confidence


def normalize_margin_text(text: str) -> str:
    value = " ".join(text.casefold().split())
    value = re.sub(r"\b\d+\b", "#", value)
    return value.strip(" |-•")


def mark_repeated_headers_and_footers(
    pages: list[PageArtifact],
    *,
    min_pages: int,
    min_fraction: float,
) -> None:
    """Mark repeated margins and finalize document-wide relationships."""

    infer_document_relationships(pages)
    infer_table_continuations(pages)
    if len(pages) < min_pages:
        return
    counts: Counter[str] = Counter()
    by_key: dict[str, list[TextBlock]] = {}
    for page in pages:
        seen_on_page: set[str] = set()
        for block in page.text_blocks:
            if block.semantic_role not in {"header", "footer", "page_number", "footnote"}:
                continue
            key = normalize_margin_text(block.text)
            if not key or key == "#":
                continue
            by_key.setdefault(key, []).append(block)
            if key not in seen_on_page:
                counts[key] += 1
                seen_on_page.add(key)

    threshold = max(min_pages, int(len(pages) * min_fraction + 0.9999))
    for key, count in counts.items():
        if count < threshold:
            continue
        for block in by_key[key]:
            block.repeated_margin_content = True
            if block.semantic_role == "footnote":
                block.semantic_role = "footer"
                block.semantic_confidence = max(block.semantic_confidence, 0.9)
