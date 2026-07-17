"""Markdown, text, metrics, and rendering projections."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pymupdf

from .models import PageArtifact


def render_page(page: pymupdf.Page, target: Path, dpi: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    pixmap = page.get_pixmap(dpi=dpi, alpha=False, annots=True)
    pixmap.save(target)


def page_metrics(page: PageArtifact) -> dict[str, Any]:
    return {
        "text_block_count": len(page.text_blocks),
        "text_character_count": sum(len(block.text) for block in page.text_blocks),
        "table_count": len(page.tables),
        "image_count": len(page.images),
        "drawing_count": len(page.drawings),
        "link_count": len(page.links),
        "annotation_count": len(page.annotations),
        "widget_count": len(page.widgets),
        "semantic_roles": dict(Counter(block.semantic_role for block in page.text_blocks)),
        **page.metrics,
    }


def document_statistics(pages: list[PageArtifact]) -> dict[str, Any]:
    roles = Counter(block.semantic_role for page in pages for block in page.text_blocks)
    return {
        "page_count": len(pages),
        "text_block_count": sum(len(page.text_blocks) for page in pages),
        "text_character_count": sum(len(block.text) for page in pages for block in page.text_blocks),
        "table_count": sum(len(page.tables) for page in pages),
        "image_count": sum(len(page.images) for page in pages),
        "drawing_count": sum(len(page.drawings) for page in pages),
        "link_count": sum(len(page.links) for page in pages),
        "annotation_count": sum(len(page.annotations) for page in pages),
        "widget_count": sum(len(page.widgets) for page in pages),
        "semantic_roles": dict(roles),
    }


def page_markdown(page: PageArtifact) -> str:
    text_by_id = {block.id: block for block in page.text_blocks}
    table_by_id = {table.id: table for table in page.tables}
    image_by_id = {image.id: image for image in page.images}
    lines = [f"<!-- page: {page.page_number}; label: {page.label} -->", f"## Page {page.page_number}", ""]
    for item in page.reading_order:
        if item.element_type == "text":
            block = text_by_id[item.element_id]
            text = block.text.strip()
            if not text or block.semantic_role in {"header", "footer", "page_number"}:
                continue
            if block.semantic_role == "document_title":
                lines.extend([f"# {text}", ""])
            elif block.semantic_role == "heading_1":
                lines.extend([f"## {text}", ""])
            elif block.semantic_role == "heading_2":
                lines.extend([f"### {text}", ""])
            elif block.semantic_role == "heading_3":
                lines.extend([f"#### {text}", ""])
            elif block.semantic_role == "code":
                lines.extend(["```text", text, "```", ""])
            else:
                lines.extend([text, ""])
        elif item.element_type == "table":
            lines.extend([table_by_id[item.element_id].markdown, ""])
        elif item.element_type == "image":
            image = image_by_id[item.element_id]
            if image.asset_path:
                lines.extend([f"![Image on page {page.page_number}]({image.asset_path})", ""])
    return "\n".join(lines).rstrip() + "\n"


def document_plain_text(pages: list[PageArtifact]) -> str:
    output: list[str] = []
    for page in pages:
        text_by_id = {block.id: block for block in page.text_blocks}
        for item in page.reading_order:
            if item.element_type != "text":
                continue
            block = text_by_id[item.element_id]
            if block.semantic_role in {"header", "footer", "page_number"}:
                continue
            if block.text.strip():
                output.append(block.text.strip())
    return "\n\n".join(output) + ("\n" if output else "")
