"""Stable artifact schema used by AKILAN."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .geometry import BBox
from .serialization import to_jsonable


SemanticRole = Literal[
    "document_title",
    "heading_1",
    "heading_2",
    "heading_3",
    "paragraph",
    "list_item",
    "caption",
    "code",
    "header",
    "footer",
    "page_number",
    "footnote",
    "unknown",
]


@dataclass(slots=True)
class Character:
    text: str
    bbox: BBox
    origin: tuple[float, float] | None = None
    synthetic: bool | None = None


@dataclass(slots=True)
class TextSpan:
    id: str
    text: str
    bbox: BBox
    font: str
    size: float
    color: int | None
    alpha: int | None
    flags: int
    ascender: float | None
    descender: float | None
    origin: tuple[float, float] | None
    characters: list[Character] = field(default_factory=list)


@dataclass(slots=True)
class TextLine:
    id: str
    bbox: BBox
    text: str
    direction: tuple[float, float]
    writing_mode: int
    spans: list[TextSpan]


@dataclass(slots=True)
class TextBlock:
    id: str
    bbox: BBox
    text: str
    lines: list[TextLine]
    source_block_number: int | None
    semantic_role: SemanticRole = "unknown"
    semantic_confidence: float = 0.0
    reading_order: int | None = None
    column_index: int | None = None
    inside_table: bool = False
    repeated_margin_content: bool = False
    relationships: dict[str, list[str]] = field(default_factory=dict)

    @property
    def dominant_font_size(self) -> float:
        weighted: list[tuple[float, int]] = []
        for line in self.lines:
            for span in line.spans:
                weighted.append((span.size, max(1, len(span.text.strip()))))
        if not weighted:
            return 0.0
        return sum(size * weight for size, weight in weighted) / sum(weight for _, weight in weighted)

    @property
    def font_names(self) -> list[str]:
        return sorted({span.font for line in self.lines for span in line.spans if span.font})


@dataclass(slots=True)
class TableElement:
    id: str
    bbox: BBox
    row_count: int
    column_count: int
    rows: list[list[str | None]]
    cells: list[list[float] | None]
    markdown: str
    reading_order: int | None = None
    extraction_strategy: str = "pymupdf.find_tables"


@dataclass(slots=True)
class ImageElement:
    id: str
    bbox: BBox
    xref: int | None
    occurrence: int
    pixel_width: int | None
    pixel_height: int | None
    colorspace: int | None
    bits_per_component: int | None
    extension: str | None
    asset_path: str | None
    digest_sha256: str | None
    transform: list[float] | None = None
    source: str = "page.get_images"
    reading_order: int | None = None


@dataclass(slots=True)
class DrawingElement:
    id: str
    bbox: BBox
    drawing_type: str | None
    fill: Any
    color: Any
    width: float | None
    opacity: float | None
    close_path: bool | None
    layer: str | None
    sequence_number: int | None
    items: list[Any]
    reading_order: int | None = None


@dataclass(slots=True)
class LinkElement:
    id: str
    bbox: BBox
    kind: int
    target_page: int | None
    target_point: list[float] | None
    uri: str | None
    file: str | None
    xref: int | None


@dataclass(slots=True)
class AnnotationElement:
    id: str
    bbox: BBox
    xref: int
    annotation_type: list[Any]
    info: dict[str, Any]
    colors: dict[str, Any]
    border: dict[str, Any]
    flags: int
    opacity: float


@dataclass(slots=True)
class WidgetElement:
    id: str
    bbox: BBox
    xref: int
    field_name: str | None
    field_label: str | None
    field_type: int | None
    field_type_string: str | None
    field_value: Any
    field_flags: int | None


@dataclass(slots=True)
class ReadingOrderItem:
    order: int
    element_type: Literal["text", "table", "image", "drawing"]
    element_id: str
    bbox: BBox
    column_index: int | None = None


@dataclass(slots=True)
class PageArtifact:
    page_index: int
    page_number: int
    label: str
    width: float
    height: float
    rotation: int
    mediabox: BBox
    cropbox: BBox
    text_blocks: list[TextBlock] = field(default_factory=list)
    tables: list[TableElement] = field(default_factory=list)
    images: list[ImageElement] = field(default_factory=list)
    drawings: list[DrawingElement] = field(default_factory=list)
    links: list[LinkElement] = field(default_factory=list)
    annotations: list[AnnotationElement] = field(default_factory=list)
    widgets: list[WidgetElement] = field(default_factory=list)
    reading_order: list[ReadingOrderItem] = field(default_factory=list)
    markdown_path: str | None = None
    json_path: str | None = None
    render_path: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentArtifact:
    schema_version: str
    generator: dict[str, str]
    source: dict[str, Any]
    document: dict[str, Any]
    table_of_contents: list[Any]
    embedded_files: list[dict[str, Any]]
    pages: list[PageArtifact]
    statistics: dict[str, Any]
    artifact_files: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)
