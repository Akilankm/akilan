from __future__ import annotations

from .models import GroupChunk, ImageChunk, PageChunk, PageChunks, TableChunk, TextChunk


def _walk_chunks(chunks: list[PageChunk]) -> list[PageChunk]:
    result: list[PageChunk] = []

    for chunk in chunks:
        result.append(chunk)
        if chunk.type == "group":
            result.extend(_walk_chunks(chunk.children))

    return result


def get_all_chunks(page: PageChunks) -> list[PageChunk]:
    return _walk_chunks(page.chunks)


def get_text_chunks(page: PageChunks) -> list[TextChunk]:
    return [chunk for chunk in get_all_chunks(page) if chunk.type == "text"]


def get_image_chunks(page: PageChunks) -> list[ImageChunk]:
    return [chunk for chunk in get_all_chunks(page) if chunk.type == "image"]


def get_table_chunks(page: PageChunks) -> list[TableChunk]:
    return [chunk for chunk in get_all_chunks(page) if chunk.type == "table"]


def get_group_chunks(page: PageChunks) -> list[GroupChunk]:
    return [chunk for chunk in get_all_chunks(page) if chunk.type == "group"]


def get_page_text(page: PageChunks, tagged: bool = False) -> str:
    text_chunks = get_text_chunks(page)
    if tagged:
        return "\n\n".join(chunk.content_tagged for chunk in text_chunks)
    return "\n\n".join(chunk.content for chunk in text_chunks)


def page_to_dict(page: PageChunks) -> dict:
    return page.to_dict()


def document_to_dict(pages: list[PageChunks]) -> dict:
    return {"pages": [page.to_dict() for page in pages]}