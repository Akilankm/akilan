from __future__ import annotations

import base64
import html
from typing import Optional

import fitz

from .base import BasePdfParser
from .models import (
    BBox,
    GroupChunk,
    ImageChunk,
    PageChunk,
    PageChunks,
    TableChunk,
    TextChunk,
)


class PdfPageParser(BasePdfParser):
    def __init__(self, pdf_path: Optional[str] = None):
        super().__init__(pdf_path=pdf_path, component="page_parser")

    # ----------------------------
    # Generic helpers
    # ----------------------------

    def _merge_bboxes(self, boxes: list[BBox]) -> BBox:
        if not boxes:
            raise ValueError("boxes must not be empty")

        merged = boxes[0]
        for box in boxes[1:]:
            merged = merged.union(box)
        return merged

    def _group_bbox(self, children: list[PageChunk]) -> BBox:
        return self._merge_bboxes([child.bbox for child in children])

    def _sort_chunks_reading_order(self, chunks: list[PageChunk]) -> list[PageChunk]:
        return sorted(
            chunks,
            key=lambda chunk: (
                chunk.bbox.y0,
                chunk.bbox.x0,
                0 if chunk.type == "text" else 1 if chunk.type == "group" else 2,
            ),
        )

    def _position_label(self, bbox: BBox, page_width: float) -> str:
        cx = bbox.cx
        if cx < page_width * 0.33:
            return "LEFT"
        if cx < page_width * 0.66:
            return "CENTER"
        return "RIGHT"

    def _reset_positions_recursive(self, chunk: PageChunk) -> None:
        chunk.position = None
        if chunk.type == "group":
            for child in chunk.children:
                self._reset_positions_recursive(child)

    def _assign_chunk_indexes_recursive(self, chunks: list[PageChunk]) -> None:
        counter = 0

        def walk(chunk: PageChunk) -> None:
            nonlocal counter
            chunk.chunk_index = counter
            counter += 1
            if chunk.type == "group":
                for child in chunk.children:
                    walk(child)

        for chunk in chunks:
            walk(chunk)

    def _bbox_vertical_contains(self, outer: BBox, inner: BBox, tolerance: float = 6.0) -> bool:
        return inner.y0 >= outer.y0 - tolerance and inner.y1 <= outer.y1 + tolerance

    # ----------------------------
    # Text helpers
    # ----------------------------

    def _extract_text_from_block(self, block: dict) -> str:
        parts: list[str] = []

        for line in block.get("lines", []):
            line_parts: list[str] = []

            for span in line.get("spans", []):
                if "text" in span:
                    text = span.get("text", "")
                else:
                    text = "".join(ch.get("c", "") for ch in span.get("chars", []))

                if text:
                    line_parts.append(text)

            line_text = "".join(line_parts).strip()
            if line_text:
                parts.append(line_text)

        return "\n".join(parts).strip()

    def _span_text(self, span: dict) -> str:
        if "text" in span:
            return span.get("text", "")
        return "".join(ch.get("c", "") for ch in span.get("chars", []))

    def _horizontal_tag_for_segment(self, segment_bbox: BBox, page_width: float) -> str:
        cx = segment_bbox.cx
        if cx < page_width * 0.33:
            return "LEFT"
        if cx < page_width * 0.66:
            return "CENTER"
        return "RIGHT"

    def _build_tagged_text_for_block(self, block: dict, page_width: float) -> str:
        line_xml_parts: list[str] = []

        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue

            prepared_spans = []
            for span in spans:
                bbox = span.get("bbox")
                if not bbox:
                    continue

                text = self._span_text(span)
                if text == "":
                    continue

                prepared_spans.append(
                    {
                        "bbox": self.bbox_from_tuple(bbox),
                        "text": text,
                    }
                )

            if not prepared_spans:
                continue

            prepared_spans.sort(key=lambda item: item["bbox"].x0)

            segments: list[dict] = []
            current_text_parts: list[str] = []
            current_boxes: list[BBox] = []

            avg_height = sum(s["bbox"].height for s in prepared_spans) / max(1, len(prepared_spans))
            gap_threshold = max(18.0, avg_height * 1.8)

            previous_bbox: Optional[BBox] = None

            for item in prepared_spans:
                bbox = item["bbox"]
                text = item["text"]

                if previous_bbox is None:
                    current_text_parts = [text]
                    current_boxes = [bbox]
                    previous_bbox = bbox
                    continue

                gap = bbox.x0 - previous_bbox.x1

                if gap > gap_threshold:
                    segment_bbox = self._merge_bboxes(current_boxes)
                    segment_text = "".join(current_text_parts).strip()
                    if segment_text:
                        segments.append({"bbox": segment_bbox, "text": segment_text})
                    current_text_parts = [text]
                    current_boxes = [bbox]
                else:
                    current_text_parts.append(text)
                    current_boxes.append(bbox)

                previous_bbox = bbox

            if current_text_parts and current_boxes:
                segment_bbox = self._merge_bboxes(current_boxes)
                segment_text = "".join(current_text_parts).strip()
                if segment_text:
                    segments.append({"bbox": segment_bbox, "text": segment_text})

            if not segments:
                continue

            segment_xml_parts: list[str] = []
            for segment in segments:
                tag = self._horizontal_tag_for_segment(segment["bbox"], page_width=page_width)
                escaped_text = html.escape(segment["text"], quote=False)
                segment_xml_parts.append(f"<{tag}>{escaped_text}</{tag}>")

            line_xml_parts.append(f"<LINE>{''.join(segment_xml_parts)}</LINE>")

        return f"<TEXT>{''.join(line_xml_parts)}</TEXT>"

    # ----------------------------
    # Table helpers
    # ----------------------------

    def _extract_tables(
        self,
        page,
        page_number: int,
        include_table_base64: bool,
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

            bbox = self.bbox_from_tuple(table.bbox)

            content = None
            mime_type = None

            if include_table_base64:
                try:
                    content = self.render_bbox_to_base64(
                        page=page,
                        bbox=bbox,
                        zoom=2.0,
                        padding=2.0,
                    )
                    mime_type = "image/png"
                except Exception as exc:
                    self.log.warning("Table rendering failed on page %s: %s", page_number, exc)

            tables.append(
                TableChunk(
                    chunk_index=-1,
                    page_number=page_number,
                    type="table",
                    bbox=bbox,
                    content=content,
                    mime_type=mime_type,
                    position=None,
                )
            )

        return tables

    # ----------------------------
    # Image helpers
    # ----------------------------

    def _block_area_ratio_to_page(self, bbox: BBox, page_rect: fitz.Rect) -> float:
        page_area = max(1.0, page_rect.width * page_rect.height)
        return bbox.area / page_area

    def _is_probable_background_image(
        self,
        bbox: BBox,
        page_rect: fitz.Rect,
        area_threshold: float = 0.90,
        edge_tolerance: float = 3.0,
    ) -> bool:
        ratio = self._block_area_ratio_to_page(bbox, page_rect)

        near_full_page = (
            abs(bbox.x0 - page_rect.x0) <= edge_tolerance
            and abs(bbox.y0 - page_rect.y0) <= edge_tolerance
            and abs(bbox.x1 - page_rect.x1) <= edge_tolerance
            and abs(bbox.y1 - page_rect.y1) <= edge_tolerance
        )

        return ratio >= area_threshold or near_full_page

    def _block_inside_any_table(self, block_bbox: BBox, tables: list[TableChunk]) -> bool:
        return any(self.intersects(block_bbox, table.bbox) for table in tables)

    # ----------------------------
    # Layout grouping helpers
    # ----------------------------

    def _cluster_into_vertical_lanes(
        self,
        items: list[PageChunk],
        page_width: float,
    ) -> list[list[PageChunk]]:
        """
        Cluster chunks by x-position into column-like lanes.
        """
        ordered = sorted(items, key=lambda c: c.bbox.cx)
        lanes: list[list[PageChunk]] = []

        for chunk in ordered:
            placed = False
            for lane in lanes:
                lane_box = self._group_bbox(lane)

                overlap = self.horizontal_overlap_ratio(lane_box, chunk.bbox)
                center_delta = abs(lane_box.cx - chunk.bbox.cx)
                allowable_center_delta = max(50.0, page_width * 0.12)

                if overlap >= 0.25 or center_delta <= allowable_center_delta:
                    lane.append(chunk)
                    placed = True
                    break

            if not placed:
                lanes.append([chunk])

        for lane in lanes:
            lane.sort(key=lambda c: (c.bbox.y0, c.bbox.x0))

        lanes.sort(key=lambda lane: min(item.bbox.x0 for item in lane))
        return lanes

    def _find_horizontal_groups_by_lane_span(
        self,
        items: list[PageChunk],
        page_number: int,
        page_width: float,
        page_height: float,
    ) -> list[PageChunk]:
        """
        Build horizontal groups by:
        1. finding vertical lanes (columns)
        2. pairing neighboring lanes when their vertical spans overlap strongly
        3. letting each lane contribute multiple stacked children inside that shared region
        """
        if not items:
            return []

        items = self._sort_chunks_reading_order(items)
        lanes = self._cluster_into_vertical_lanes(items, page_width=page_width)

        if len(lanes) <= 1:
            return self._build_vertical_groups(items, page_number, page_width, page_height)

        lane_boxes = [self._group_bbox(lane) for lane in lanes]
        used = [False] * len(lanes)
        result: list[PageChunk] = []

        i = 0
        while i < len(lanes):
            if used[i]:
                i += 1
                continue

            current_indices = [i]
            used[i] = True
            current_box = lane_boxes[i]

            j = i + 1
            while j < len(lanes):
                if used[j]:
                    j += 1
                    continue

                overlap_ratio = self.vertical_overlap_ratio(current_box, lane_boxes[j])
                if overlap_ratio >= 0.35:
                    current_indices.append(j)
                    used[j] = True
                    current_box = current_box.union(lane_boxes[j])
                    j += 1
                else:
                    break

            if len(current_indices) == 1:
                lane_items = lanes[current_indices[0]]
                result.extend(
                    self._build_vertical_groups(
                        lane_items,
                        page_number=page_number,
                        page_width=page_width,
                        page_height=page_height,
                    )
                )
            else:
                children: list[PageChunk] = []

                group_region = lane_boxes[current_indices[0]]
                for idx in current_indices[1:]:
                    group_region = group_region.union(lane_boxes[idx])

                for idx in current_indices:
                    lane_items = lanes[idx]

                    lane_in_region = [
                        item for item in lane_items
                        if self._bbox_vertical_contains(group_region, item.bbox, tolerance=10.0)
                    ]

                    if not lane_in_region:
                        continue

                    lane_child_nodes = self._build_vertical_groups(
                        lane_in_region,
                        page_number=page_number,
                        page_width=page_width,
                        page_height=page_height,
                    )

                    if len(lane_child_nodes) == 1:
                        child = lane_child_nodes[0]
                    else:
                        for node in lane_child_nodes:
                            self._reset_positions_recursive(node)

                        child = GroupChunk(
                            chunk_index=-1,
                            page_number=page_number,
                            type="group",
                            layout="vertical",
                            bbox=self._group_bbox(lane_child_nodes),
                            children=lane_child_nodes,
                            position=None,
                        )

                    child.position = self._position_label(child.bbox, page_width)
                    children.append(child)

                children = sorted(children, key=lambda c: c.bbox.x0)

                for child in children:
                    if child.type == "group":
                        for sub in child.children:
                            self._reset_positions_recursive(sub)

                result.append(
                    GroupChunk(
                        chunk_index=-1,
                        page_number=page_number,
                        type="group",
                        layout="horizontal",
                        bbox=self._group_bbox(children),
                        children=children,
                        position=None,
                    )
                )

            i += 1

        return self._sort_chunks_reading_order(result)

    def _are_same_vertical_stack(
        self,
        a: PageChunk,
        b: PageChunk,
        page_height: float,
    ) -> bool:
        overlap = self.horizontal_overlap_ratio(a.bbox, b.bbox)
        if overlap < 0.30:
            return False

        gap = max(0.0, b.bbox.y0 - a.bbox.y1)
        allowable_gap = max(28.0, page_height * 0.06)
        return gap <= allowable_gap

    def _build_vertical_groups(
        self,
        items: list[PageChunk],
        page_number: int,
        page_width: float,
        page_height: float,
    ) -> list[PageChunk]:
        """
        Build vertical groups inside a lane / column.
        """
        if not items:
            return []

        ordered = sorted(items, key=lambda c: (c.bbox.y0, c.bbox.x0))
        runs: list[list[PageChunk]] = []

        i = 0
        while i < len(ordered):
            run = [ordered[i]]
            j = i + 1

            while j < len(ordered):
                if self._are_same_vertical_stack(run[-1], ordered[j], page_height=page_height):
                    run.append(ordered[j])
                    j += 1
                else:
                    break

            runs.append(run)
            i = j

        result: list[PageChunk] = []

        for run in runs:
            if len(run) == 1:
                single = run[0]
                self._reset_positions_recursive(single)
                result.append(single)
            else:
                for child in run:
                    self._reset_positions_recursive(child)

                result.append(
                    GroupChunk(
                        chunk_index=-1,
                        page_number=page_number,
                        type="group",
                        layout="vertical",
                        bbox=self._group_bbox(run),
                        children=run,
                        position=None,
                    )
                )

        return result

    # ----------------------------
    # Core parse
    # ----------------------------

    def _parse_page_from_doc(
        self,
        doc,
        page_number: int,
        include_table_base64: bool,
        include_image_base64: bool,
        skip_background_images: bool,
        enable_grouping: bool,
    ) -> PageChunks:
        page = self.get_page(doc, page_number)
        page_rect = page.rect

        tables = self._extract_tables(
            page=page,
            page_number=page_number,
            include_table_base64=include_table_base64,
        )

        raw = page.get_text("rawdict")
        blocks = raw.get("blocks", [])

        atomic_chunks: list[PageChunk] = []

        for block in blocks:
            block_type = block.get("type")
            bbox_tuple = block.get("bbox")
            if not bbox_tuple:
                continue

            bbox = self.bbox_from_tuple(bbox_tuple)

            if self._block_inside_any_table(bbox, tables):
                continue

            if block_type == 0:
                text = self._extract_text_from_block(block)
                if not text:
                    continue

                content_tagged = self._build_tagged_text_for_block(
                    block=block,
                    page_width=float(page_rect.width),
                )

                atomic_chunks.append(
                    TextChunk(
                        chunk_index=-1,
                        page_number=page_number,
                        type="text",
                        bbox=bbox,
                        content=text,
                        content_tagged=content_tagged,
                        position=None,
                    )
                )

            elif block_type == 1:
                if skip_background_images and self._is_probable_background_image(
                    bbox=bbox,
                    page_rect=page_rect,
                ):
                    continue

                content = None
                mime_type = None

                if include_image_base64:
                    image_bytes = block.get("image")
                    ext = (block.get("ext") or "png").lower()

                    if image_bytes:
                        content = base64.b64encode(image_bytes).decode("utf-8")
                        mime_type = f"image/{ext}"

                atomic_chunks.append(
                    ImageChunk(
                        chunk_index=-1,
                        page_number=page_number,
                        type="image",
                        bbox=bbox,
                        content=content,
                        mime_type=mime_type,
                        position=None,
                    )
                )

        for table in tables:
            atomic_chunks.append(table)

        if enable_grouping:
            chunks = self._find_horizontal_groups_by_lane_span(
                items=atomic_chunks,
                page_number=page_number,
                page_width=float(page_rect.width),
                page_height=float(page_rect.height),
            )
        else:
            chunks = self._sort_chunks_reading_order(atomic_chunks)
            for chunk in chunks:
                self._reset_positions_recursive(chunk)

        self._assign_chunk_indexes_recursive(chunks)

        return PageChunks(
            page_number=page_number,
            width=float(page_rect.width),
            height=float(page_rect.height),
            chunks=chunks,
        )

    def parse_page(
        self,
        page_number: int,
        include_table_base64: bool = True,
        include_image_base64: bool = True,
        skip_background_images: bool = True,
        enable_grouping: bool = True,
    ) -> PageChunks:
        doc = self.open_pdf()

        try:
            return self._parse_page_from_doc(
                doc=doc,
                page_number=page_number,
                include_table_base64=include_table_base64,
                include_image_base64=include_image_base64,
                skip_background_images=skip_background_images,
                enable_grouping=enable_grouping,
            )
        finally:
            doc.close()

    def parse_document(
        self,
        include_table_base64: bool = True,
        include_image_base64: bool = True,
        skip_background_images: bool = True,
        enable_grouping: bool = True,
    ) -> list[PageChunks]:
        doc = self.open_pdf()

        try:
            pages: list[PageChunks] = []

            for page_number in range(1, len(doc) + 1):
                pages.append(
                    self._parse_page_from_doc(
                        doc=doc,
                        page_number=page_number,
                        include_table_base64=include_table_base64,
                        include_image_base64=include_image_base64,
                        skip_background_images=skip_background_images,
                        enable_grouping=enable_grouping,
                    )
                )

            return pages
        finally:
            doc.close()