from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional, Union


@dataclass
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0

    def union(self, other: "BBox") -> "BBox":
        return BBox(
            x0=min(self.x0, other.x0),
            y0=min(self.y0, other.y0),
            x1=max(self.x1, other.x1),
            y1=max(self.y1, other.y1),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TextChunk:
    chunk_index: int
    page_number: int
    type: Literal["text"]
    bbox: BBox
    content: str
    content_tagged: str
    position: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "type": self.type,
            "bbox": self.bbox.to_dict(),
            "content": self.content,
            "content_tagged": self.content_tagged,
            "position": self.position,
        }


@dataclass
class ImageChunk:
    chunk_index: int
    page_number: int
    type: Literal["image"]
    bbox: BBox
    content: Optional[str] = None
    mime_type: Optional[str] = None
    position: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "type": self.type,
            "bbox": self.bbox.to_dict(),
            "content": self.content,
            "mime_type": self.mime_type,
            "position": self.position,
        }


@dataclass
class TableChunk:
    chunk_index: int
    page_number: int
    type: Literal["table"]
    bbox: BBox
    content: Optional[str] = None
    mime_type: Optional[str] = None
    position: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "type": self.type,
            "bbox": self.bbox.to_dict(),
            "content": self.content,
            "mime_type": self.mime_type,
            "position": self.position,
        }


@dataclass
class GroupChunk:
    chunk_index: int
    page_number: int
    type: Literal["group"]
    layout: Literal["horizontal", "vertical"]
    bbox: BBox
    children: list["PageChunk"] = field(default_factory=list)
    position: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "type": self.type,
            "layout": self.layout,
            "bbox": self.bbox.to_dict(),
            "position": self.position,
            "children": [child.to_dict() for child in self.children],
        }


PageChunk = Union[TextChunk, ImageChunk, TableChunk, GroupChunk]


@dataclass
class PageChunks:
    page_number: int
    width: float
    height: float
    chunks: list[PageChunk] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }