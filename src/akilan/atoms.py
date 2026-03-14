from __future__ import annotations

import base64
import hashlib
import html
import re
from typing import Optional

from .base import BasePdfComponent
from .models import (
    AbsolutePositionCoarse,
    AtomDebug,
    BBox,
    DynamicPosition,
    ImageChunk,
    NormalizedPosition,
    NormalizedSize,
    PageChunk,
    TableChunk,
    TextChunk,
)


class PdfAtomExtractor(BasePdfComponent):
    """
    Extract atomic chunks only:
    - text
    - image
    - table

    Focus:
    - completeness
    - purity
    - stability
    - rich payloads
    """

    TABLE_TEXT_OVERLAP_DROP_THRESHOLD = 0.60
    IMAGE_DEDUP_IOU_THRESHOLD = 0.92
    TABLE_DEDUP_IOU_THRESHOLD = 0.90
    BACKGROUND_TEXT_COVERAGE_THRESHOLD = 0.55
    BACKGROUND_AREA_THRESHOLD = 0.90

    def __init__(self, pdf_path: Optional[str] = None):
        super().__init__(pdf_path=pdf_path, component="atoms")

    # ---------------------------------------------------------
    # Basic geometry / metadata helpers
    # ---------------------------------------------------------

    def _merge_bboxes(self, boxes: list[BBox]) -> BBox:
        if not boxes:
            raise ValueError("boxes must not be empty")
        merged = boxes[0]
        for box in boxes[1:]:
            merged = merged.union(box)
        return merged

    def _coarse_position(
        self,
        bbox: BBox,
        page_width: float,
        page_height: float,
    ) -> AbsolutePositionCoarse:
        if bbox.cx < page_width * 0.33:
            x_bucket = "LEFT"
        elif bbox.cx < page_width * 0.66:
            x_bucket = "CENTER"
        else:
            x_bucket = "RIGHT"

        if bbox.cy < page_height * 0.33:
            y_bucket = "TOP"
        elif bbox.cy < page_height * 0.66:
            y_bucket = "MIDDLE"
        else:
            y_bucket = "BOTTOM"

        return f"{y_bucket}_{x_bucket}"  # type: ignore[return-value]

    def _normalized_position(self, bbox: BBox, page_width: float, page_height: float) -> NormalizedPosition:
        return NormalizedPosition(
            x=0.0 if page_width <= 0 else bbox.cx / page_width,
            y=0.0 if page_height <= 0 else bbox.cy / page_height,
        )

    def _normalized_size(self, bbox: BBox, page_width: float, page_height: float) -> NormalizedSize:
        return NormalizedSize(
            w=0.0 if page_width <= 0 else bbox.width / page_width,
            h=0.0 if page_height <= 0 else bbox.height / page_height,
        )

    def _make_text_chunk(
        self,
        page_number: int,
        bbox: BBox,
        content_raw: str,
        content_clean: str,
        content_tagged: str,
        page_width: float,
        page_height: float,
        debug: AtomDebug,
    ) -> TextChunk:
        return TextChunk(
            chunk_index=-1,
            page_number=page_number,
            type="text",
            bbox=bbox,
            content=content_clean,
            content_raw=content_raw,
            content_tagged=content_tagged,
            position_normalized=self._normalized_position(bbox, page_width, page_height),
            size_normalized=self._normalized_size(bbox, page_width, page_height),
            absolute_position_coarse=self._coarse_position(bbox, page_width, page_height),
            absolute_position_dynamic=None,
            relative_position=None,
            debug=debug,
        )

    def _make_image_chunk(
        self,
        page_number: int,
        bbox: BBox,
        page_width: float,
        page_height: float,
        content: Optional[str],
        mime_type: Optional[str],
        debug: AtomDebug,
    ) -> ImageChunk:
        return ImageChunk(
            chunk_index=-1,
            page_number=page_number,
            type="image",
            bbox=bbox,
            content=content,
            mime_type=mime_type,
            position_normalized=self._normalized_position(bbox, page_width, page_height),
            size_normalized=self._normalized_size(bbox, page_width, page_height),
            absolute_position_coarse=self._coarse_position(bbox, page_width, page_height),
            absolute_position_dynamic=None,
            relative_position=None,
            debug=debug,
        )

    def _make_table_chunk(
        self,
        page_number: int,
        bbox: BBox,
        page_width: float,
        page_height: float,
        content: Optional[str],
        mime_type: Optional[str],
        debug: AtomDebug,
    ) -> TableChunk:
        return TableChunk(
            chunk_index=-1,
            page_number=page_number,
            type="table",
            bbox=bbox,
            content=content,
            mime_type=mime_type,
            position_normalized=self._normalized_position(bbox, page_width, page_height),
            size_normalized=self._normalized_size(bbox, page_width, page_height),
            absolute_position_coarse=self._coarse_position(bbox, page_width, page_height),
            absolute_position_dynamic=None,
            relative_position=None,
            debug=debug,
        )

    # ---------------------------------------------------------
    # Text extraction
    # ---------------------------------------------------------

    def _span_text(self, span: dict) -> str:
        if "text" in span:
            return span.get("text", "")
        return "".join(ch.get("c", "") for ch in span.get("chars", []))

    def _minimal_text_normalize(self, text: str) -> str:
        """
        Keep this conservative.
        Fix only the gremlins:
        - normalize CRLF
        - remove null chars
        - strip trailing spaces per line
        - collapse 3+ blank lines to 2
        """
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", "")
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip("\n")

    def _extract_text_from_block(self, block: dict) -> tuple[str, str, AtomDebug]:
        raw_lines: list[str] = []
        line_count = 0
        span_count = 0

        for line in block.get("lines", []):
            line_count += 1
            parts: list[str] = []

            for span in line.get("spans", []):
                span_count += 1
                text = self._span_text(span)
                if text:
                    parts.append(text)

            # Do not .strip() aggressively here.
            line_text = "".join(parts)
            raw_lines.append(line_text)

        content_raw = "\n".join(raw_lines)
        content_clean = self._minimal_text_normalize(content_raw)

        debug = AtomDebug(
            line_count=line_count,
            span_count=span_count,
            char_count_raw=len(content_raw),
            char_count_clean=len(content_clean),
            source_block_type=block.get("type"),
        )
        return content_raw, content_clean, debug

    def _segment_tag(self, bbox: BBox, page_width: float, page_height: float) -> str:
        if bbox.cx < page_width * 0.33:
            x_tag = "LEFT"
        elif bbox.cx < page_width * 0.66:
            x_tag = "CENTER"
        else:
            x_tag = "RIGHT"

        if bbox.cy < page_height * 0.33:
            y_tag = "TOP"
        elif bbox.cy < page_height * 0.66:
            y_tag = "MIDDLE"
        else:
            y_tag = "BOTTOM"

        return f"{y_tag}_{x_tag}"

    def _build_tagged_text_for_block(
        self,
        block: dict,
        page_width: float,
        page_height: float,
    ) -> str:
        line_xml_parts: list[str] = []

        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue

            prepared = []
            for span in spans:
                bbox = span.get("bbox")
                if not bbox:
                    continue
                text = self._span_text(span)
                if text == "":
                    continue
                prepared.append({"bbox": self.bbox_from_tuple(bbox), "text": text})

            if not prepared:
                continue

            prepared.sort(key=lambda item: item["bbox"].x0)

            avg_height = sum(s["bbox"].height for s in prepared) / max(1, len(prepared))
            gap_threshold = max(18.0, avg_height * 1.8)

            segments: list[dict] = []
            current_text_parts: list[str] = []
            current_boxes: list[BBox] = []
            previous_bbox: Optional[BBox] = None

            for item in prepared:
                bbox = item["bbox"]
                text = item["text"]

                if previous_bbox is None:
                    current_text_parts = [text]
                    current_boxes = [bbox]
                    previous_bbox = bbox
                    continue

                gap = bbox.x0 - previous_bbox.x1
                if gap > gap_threshold:
                    seg_bbox = self._merge_bboxes(current_boxes)
                    seg_text = "".join(current_text_parts)
                    if seg_text:
                        segments.append({"bbox": seg_bbox, "text": seg_text})
                    current_text_parts = [text]
                    current_boxes = [bbox]
                else:
                    current_text_parts.append(text)
                    current_boxes.append(bbox)

                previous_bbox = bbox

            if current_text_parts and current_boxes:
                seg_bbox = self._merge_bboxes(current_boxes)
                seg_text = "".join(current_text_parts)
                if seg_text:
                    segments.append({"bbox": seg_bbox, "text": seg_text})

            if not segments:
                continue

            segment_xml_parts: list[str] = []
            for segment in segments:
                tag = self._segment_tag(segment["bbox"], page_width, page_height)
                escaped = html.escape(segment["text"], quote=False)
                segment_xml_parts.append(f"<{tag}>{escaped}</{tag}>")

            line_xml_parts.append(f"<LINE>{''.join(segment_xml_parts)}</LINE>")

        return f"<TEXT>{''.join(line_xml_parts)}</TEXT>"

    # ---------------------------------------------------------
    # Table extraction
    # ---------------------------------------------------------

    def _extract_tables(
        self,
        page,
        page_number: int,
        include_table_base64: bool,
        page_width: float,
        page_height: float,
    ) -> list[TableChunk]:
        tables: list[TableChunk] = []

        try:
            table_finder = page.find_tables()
        except Exception as exc:
            self.log.warning("Table detection failed on page %s: %s", page_number, exc)
            return tables

        for table in table_finder.tables:
            if not table.bbox:
                continue

            x0, y0, x1, y1 = table.bbox
            # small padding helps completeness
            padded_bbox = BBox(
                max(0.0, float(x0) - 2.0),
                max(0.0, float(y0) - 2.0),
                float(x1) + 2.0,
                float(y1) + 2.0,
            )

            content = None
            mime_type = None

            if include_table_base64:
                try:
                    content = self.render_bbox_to_base64(
                        page=page,
                        bbox=padded_bbox,
                        zoom=2.0,
                        padding=0.0,
                    )
                    mime_type = "image/png"
                except Exception as exc:
                    self.log.warning("Table rendering failed on page %s: %s", page_number, exc)

            debug = AtomDebug(
                source_block_type=None,
                source_ext="png",
                char_count_raw=0,
                char_count_clean=0,
            )

            tables.append(
                self._make_table_chunk(
                    page_number=page_number,
                    bbox=padded_bbox,
                    page_width=page_width,
                    page_height=page_height,
                    content=content,
                    mime_type=mime_type,
                    debug=debug,
                )
            )

        return self._dedupe_tables(tables)

    def _dedupe_tables(self, tables: list[TableChunk]) -> list[TableChunk]:
        if not tables:
            return []

        kept: list[TableChunk] = []

        for table in sorted(tables, key=lambda t: t.bbox.area, reverse=True):
            duplicate = False
            for existing in kept:
                if table.bbox.iou(existing.bbox) >= self.TABLE_DEDUP_IOU_THRESHOLD:
                    duplicate = True
                    break
            if not duplicate:
                kept.append(table)

        kept.sort(key=lambda t: (t.bbox.y0, t.bbox.x0))
        return kept

    # ---------------------------------------------------------
    # Image extraction
    # ---------------------------------------------------------

    def _block_area_ratio_to_page(self, bbox: BBox, page_rect) -> float:
        page_area = max(1.0, page_rect.width * page_rect.height)
        return bbox.area / page_area

    def _text_coverage_inside_bbox(self, text_blocks: list[BBox], bbox: BBox) -> float:
        if bbox.area <= 0:
            return 0.0

        covered_area = 0.0
        for text_bbox in text_blocks:
            inter = bbox.intersection(text_bbox)
            if inter is not None:
                covered_area += inter.area

        return covered_area / bbox.area

    def _is_probable_background_image(
        self,
        bbox: BBox,
        page_rect,
        text_bboxes: list[BBox],
        edge_tolerance: float = 3.0,
    ) -> bool:
        ratio = self._block_area_ratio_to_page(bbox, page_rect)
        near_full_page = (
            abs(bbox.x0 - page_rect.x0) <= edge_tolerance
            and abs(bbox.y0 - page_rect.y0) <= edge_tolerance
            and abs(bbox.x1 - page_rect.x1) <= edge_tolerance
            and abs(bbox.y1 - page_rect.y1) <= edge_tolerance
        )
        text_coverage = self._text_coverage_inside_bbox(text_bboxes, bbox)

        return (
            ratio >= self.BACKGROUND_AREA_THRESHOLD
            or near_full_page
            or (ratio >= 0.65 and text_coverage >= self.BACKGROUND_TEXT_COVERAGE_THRESHOLD)
        )

    def _image_signature(self, chunk: ImageChunk) -> str:
        debug = chunk.debug
        payload_id = ""
        if chunk.content:
            payload_id = hashlib.sha1(chunk.content[:2048].encode("utf-8")).hexdigest()[:12]

        ext = debug.source_ext if debug else ""
        pw = debug.pixel_width if debug and debug.pixel_width is not None else -1
        ph = debug.pixel_height if debug and debug.pixel_height is not None else -1

        return f"{ext}|{pw}|{ph}|{payload_id}"

    def _dedupe_images(self, images: list[ImageChunk]) -> list[ImageChunk]:
        if not images:
            return []

        kept: list[ImageChunk] = []

        # Prefer larger / richer images first
        ordered = sorted(
            images,
            key=lambda img: (
                img.bbox.area,
                1 if img.content else 0,
            ),
            reverse=True,
        )

        for image in ordered:
            duplicate = False
            sig = self._image_signature(image)

            for existing in kept:
                same_sig = sig == self._image_signature(existing)
                strong_overlap = image.bbox.iou(existing.bbox) >= self.IMAGE_DEDUP_IOU_THRESHOLD
                contained = (
                    image.bbox.overlap_ratio(existing.bbox) >= 0.98
                    or existing.bbox.overlap_ratio(image.bbox) >= 0.98
                )

                if same_sig and (strong_overlap or contained):
                    duplicate = True
                    break

            if not duplicate:
                kept.append(image)

        kept.sort(key=lambda img: (img.bbox.y0, img.bbox.x0))
        return kept

    # ---------------------------------------------------------
    # Main extraction
    # ---------------------------------------------------------

    def extract_page_atoms(
        self,
        page,
        page_number: int,
        include_table_base64: bool = True,
        include_image_base64: bool = True,
        skip_background_images: bool = True,
    ) -> list[PageChunk]:
        page_rect = page.rect
        page_width = float(page_rect.width)
        page_height = float(page_rect.height)

        raw = page.get_text("rawdict")
        blocks = raw.get("blocks", [])

        # Build raw text bbox list first; helpful for image background filtering.
        raw_text_bboxes: list[BBox] = []
        for block in blocks:
            if block.get("type") == 0 and block.get("bbox"):
                raw_text_bboxes.append(self.bbox_from_tuple(block["bbox"]))

        tables = self._extract_tables(
            page=page,
            page_number=page_number,
            include_table_base64=include_table_base64,
            page_width=page_width,
            page_height=page_height,
        )
        table_boxes = [table.bbox for table in tables]

        text_chunks: list[TextChunk] = []
        image_chunks: list[ImageChunk] = []

        for block in blocks:
            block_type = block.get("type")
            bbox_tuple = block.get("bbox")
            if not bbox_tuple:
                continue

            bbox = self.bbox_from_tuple(bbox_tuple)

            if block_type == 0:
                # Drop text atom only if the overlap with a table is substantial.
                max_table_overlap = 0.0
                for table_bbox in table_boxes:
                    max_table_overlap = max(max_table_overlap, bbox.overlap_ratio(table_bbox))

                if max_table_overlap >= self.TABLE_TEXT_OVERLAP_DROP_THRESHOLD:
                    continue

                content_raw, content_clean, debug = self._extract_text_from_block(block)
                if not content_clean:
                    continue

                content_tagged = self._build_tagged_text_for_block(
                    block=block,
                    page_width=page_width,
                    page_height=page_height,
                )

                text_chunks.append(
                    self._make_text_chunk(
                        page_number=page_number,
                        bbox=bbox,
                        content_raw=content_raw,
                        content_clean=content_clean,
                        content_tagged=content_tagged,
                        page_width=page_width,
                        page_height=page_height,
                        debug=debug,
                    )
                )

            elif block_type == 1:
                if skip_background_images and self._is_probable_background_image(
                    bbox=bbox,
                    page_rect=page_rect,
                    text_bboxes=raw_text_bboxes,
                ):
                    continue

                content = None
                mime_type = None
                ext = (block.get("ext") or "png").lower()
                image_bytes = block.get("image")
                pixel_width = block.get("width")
                pixel_height = block.get("height")

                if include_image_base64 and image_bytes:
                    content = base64.b64encode(image_bytes).decode("utf-8")
                    mime_type = f"image/{ext}"

                debug = AtomDebug(
                    source_block_type=block_type,
                    source_ext=ext,
                    pixel_width=int(pixel_width) if isinstance(pixel_width, (int, float)) else None,
                    pixel_height=int(pixel_height) if isinstance(pixel_height, (int, float)) else None,
                )

                image_chunks.append(
                    self._make_image_chunk(
                        page_number=page_number,
                        bbox=bbox,
                        page_width=page_width,
                        page_height=page_height,
                        content=content,
                        mime_type=mime_type,
                        debug=debug,
                    )
                )

        image_chunks = self._dedupe_images(image_chunks)

        chunks: list[PageChunk] = []
        chunks.extend(text_chunks)
        chunks.extend(image_chunks)
        chunks.extend(tables)

        chunks.sort(key=lambda c: (c.bbox.y0, c.bbox.x0))
        return chunks
