from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional, Union


AbsolutePositionCoarse = Literal[
    "TOP_LEFT",
    "TOP_CENTER",
    "TOP_RIGHT",
    "MIDDLE_LEFT",
    "MIDDLE_CENTER",
    "MIDDLE_RIGHT",
    "BOTTOM_LEFT",
    "BOTTOM_CENTER",
    "BOTTOM_RIGHT",
]

RelativePosition = Literal[
    "LEFT",
    "CENTER",
    "RIGHT",
    "TOP",
    "MIDDLE",
    "BOTTOM",
]


@dataclass
class NormalizedPosition:
    x: float
    y: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormalizedSize:
    w: float
    h: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DynamicPosition:
    x_zone: int
    x_zone_count: int
    y_zone: int
    y_zone_count: int

    def to_dict(self) -> dict:
        return asdict(self)


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

    def intersects(self, other: "BBox") -> bool:
        return not (
            self.x1 <= other.x0
            or self.x0 >= other.x1
            or self.y1 <= other.y0
            or self.y0 >= other.y1
        )

    def intersection(self, other: "BBox") -> Optional["BBox"]:
        if not self.intersects(other):
            return None
        return BBox(
            x0=max(self.x0, other.x0),
            y0=max(self.y0, other.y0),
            x1=min(self.x1, other.x1),
            y1=min(self.y1, other.y1),
        )

    def contains(self, other: "BBox", tolerance: float = 0.0) -> bool:
        return (
            other.x0 >= self.x0 - tolerance
            and other.y0 >= self.y0 - tolerance
            and other.x1 <= self.x1 + tolerance
            and other.y1 <= self.y1 + tolerance
        )

    def overlap_ratio(self, other: "BBox") -> float:
        inter = self.intersection(other)
        if inter is None or self.area <= 0:
            return 0.0
        return inter.area / self.area

    def iou(self, other: "BBox") -> float:
        inter = self.intersection(other)
        if inter is None:
            return 0.0
        union_area = self.area + other.area - inter.area
        if union_area <= 0:
            return 0.0
        return inter.area / union_area

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AtomDebug:
    line_count: int = 0
    span_count: int = 0
    char_count_raw: int = 0
    char_count_clean: int = 0
    source_block_type: Optional[int] = None
    source_ext: Optional[str] = None
    pixel_width: Optional[int] = None
    pixel_height: Optional[int] = None
    dropped_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TextChunk:
    chunk_index: int
    page_number: int
    type: Literal["text"]
    bbox: BBox
    content: str
    content_raw: str
    content_tagged: str
    position_normalized: Optional[NormalizedPosition] = None
    size_normalized: Optional[NormalizedSize] = None
    absolute_position_coarse: Optional[AbsolutePositionCoarse] = None
    absolute_position_dynamic: Optional[DynamicPosition] = None
    relative_position: Optional[RelativePosition] = None
    debug: Optional[AtomDebug] = None

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "type": self.type,
            "bbox": self.bbox.to_dict(),
            "content": self.content,
            "content_raw": self.content_raw,
            "content_tagged": self.content_tagged,
            "position_normalized": None if self.position_normalized is None else self.position_normalized.to_dict(),
            "size_normalized": None if self.size_normalized is None else self.size_normalized.to_dict(),
            "absolute_position_coarse": self.absolute_position_coarse,
            "absolute_position_dynamic": None if self.absolute_position_dynamic is None else self.absolute_position_dynamic.to_dict(),
            "relative_position": self.relative_position,
            "debug": None if self.debug is None else self.debug.to_dict(),
        }


@dataclass
class ImageChunk:
    chunk_index: int
    page_number: int
    type: Literal["image"]
    bbox: BBox
    content: Optional[str] = None
    mime_type: Optional[str] = None
    position_normalized: Optional[NormalizedPosition] = None
    size_normalized: Optional[NormalizedSize] = None
    absolute_position_coarse: Optional[AbsolutePositionCoarse] = None
    absolute_position_dynamic: Optional[DynamicPosition] = None
    relative_position: Optional[RelativePosition] = None
    debug: Optional[AtomDebug] = None

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "type": self.type,
            "bbox": self.bbox.to_dict(),
            "content": self.content,
            "mime_type": self.mime_type,
            "position_normalized": None if self.position_normalized is None else self.position_normalized.to_dict(),
            "size_normalized": None if self.size_normalized is None else self.size_normalized.to_dict(),
            "absolute_position_coarse": self.absolute_position_coarse,
            "absolute_position_dynamic": None if self.absolute_position_dynamic is None else self.absolute_position_dynamic.to_dict(),
            "relative_position": self.relative_position,
            "debug": None if self.debug is None else self.debug.to_dict(),
        }


@dataclass
class TableChunk:
    chunk_index: int
    page_number: int
    type: Literal["table"]
    bbox: BBox
    content: Optional[str] = None
    mime_type: Optional[str] = None
    position_normalized: Optional[NormalizedPosition] = None
    size_normalized: Optional[NormalizedSize] = None
    absolute_position_coarse: Optional[AbsolutePositionCoarse] = None
    absolute_position_dynamic: Optional[DynamicPosition] = None
    relative_position: Optional[RelativePosition] = None
    debug: Optional[AtomDebug] = None

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "type": self.type,
            "bbox": self.bbox.to_dict(),
            "content": self.content,
            "mime_type": self.mime_type,
            "position_normalized": None if self.position_normalized is None else self.position_normalized.to_dict(),
            "size_normalized": None if self.size_normalized is None else self.size_normalized.to_dict(),
            "absolute_position_coarse": self.absolute_position_coarse,
            "absolute_position_dynamic": None if self.absolute_position_dynamic is None else self.absolute_position_dynamic.to_dict(),
            "relative_position": self.relative_position,
            "debug": None if self.debug is None else self.debug.to_dict(),
        }


@dataclass
class GroupChunk:
    chunk_index: int
    page_number: int
    type: Literal["group"]
    layout: Literal["horizontal", "vertical"]
    bbox: BBox
    children: list["PageChunk"] = field(default_factory=list)
    position_normalized: Optional[NormalizedPosition] = None
    size_normalized: Optional[NormalizedSize] = None
    absolute_position_coarse: Optional[AbsolutePositionCoarse] = None
    absolute_position_dynamic: Optional[DynamicPosition] = None
    relative_position: Optional[RelativePosition] = None

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "type": self.type,
            "layout": self.layout,
            "bbox": self.bbox.to_dict(),
            "position_normalized": None if self.position_normalized is None else self.position_normalized.to_dict(),
            "size_normalized": None if self.size_normalized is None else self.size_normalized.to_dict(),
            "absolute_position_coarse": self.absolute_position_coarse,
            "absolute_position_dynamic": None if self.absolute_position_dynamic is None else self.absolute_position_dynamic.to_dict(),
            "relative_position": self.relative_position,
            "children": [child.to_dict() for child in self.children],
        }


PageChunk = Union[TextChunk, ImageChunk, TableChunk, GroupChunk]


@dataclass
class PageChunks:
    page_number: int
    width: float
    height: float
    chunks: list[PageChunk] = field(default_factory=list)
    debug: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "debug": self.debug,
        }
