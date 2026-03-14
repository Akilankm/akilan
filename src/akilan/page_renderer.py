from __future__ import annotations

from pathlib import Path
from typing import Optional

import fitz
from PIL import Image, ImageDraw, ImageFont

from .base import BasePdfComponent
from .models import PageChunk, PageChunks


class PdfPageRenderer(BasePdfComponent):
    COLOR_MAP = {
        "text": (0, 102, 204),
        "image": (0, 153, 51),
        "table": (204, 0, 0),
        "group_horizontal": (255, 140, 0),
        "group_vertical": (153, 51, 255),
        "connector": (80, 80, 80),
    }

    def __init__(self, pdf_path: Optional[str] = None):
        super().__init__(pdf_path=pdf_path, component="page_renderer")

    def _get_font(self, size: int = 14):
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()

    def _chunk_color(self, chunk: PageChunk):
        if chunk.type == "group":
            return (
                self.COLOR_MAP["group_horizontal"]
                if chunk.layout == "horizontal"
                else self.COLOR_MAP["group_vertical"]
            )
        return self.COLOR_MAP.get(chunk.type, (0, 0, 0))

    def _chunk_label(self, chunk: PageChunk) -> str:
        if chunk.type == "group":
            label = f"G:{'H' if chunk.layout == 'horizontal' else 'V'}"
        else:
            label = chunk.type.upper()

        if getattr(chunk, "absolute_position_coarse", None):
            label += f" [{chunk.absolute_position_coarse}]"

        dyn = getattr(chunk, "absolute_position_dynamic", None)
        if dyn is not None:
            label += f" {{x:{dyn.x_zone}/{dyn.x_zone_count},y:{dyn.y_zone}/{dyn.y_zone_count}}}"

        if getattr(chunk, "relative_position", None):
            label += f" <{chunk.relative_position}>"

        return label

    def _scale_bbox(self, bbox, zoom: float):
        return (
            bbox.x0 * zoom,
            bbox.y0 * zoom,
            bbox.x1 * zoom,
            bbox.y1 * zoom,
        )

    def _text_size(self, draw: ImageDraw.ImageDraw, text: str, font):
        try:
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            return right - left, bottom - top
        except Exception:
            return max(20, len(text) * 7), 14

    def _rects_overlap(self, a, b) -> bool:
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        return not (ax1 <= bx0 or ax0 >= bx1 or ay1 <= by0 or ay0 >= by1)

    def _point_to_rect_distance_sq(self, px, py, rect):
        rx0, ry0, rx1, ry1 = rect
        cx = min(max(px, rx0), rx1)
        cy = min(max(py, ry0), ry1)
        dx = px - cx
        dy = py - cy
        return dx * dx + dy * dy

    def _candidate_label_boxes(
        self,
        box_rect,
        label_w,
        label_h,
        margin,
        image_w,
        image_h,
        is_group,
    ):
        x0, y0, x1, y1 = box_rect
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0

        outer = margin * (1.8 if is_group else 1.0)

        candidates = [
            ((x0, y0 - label_h - outer, x0 + label_w, y0 - outer), (x0, y0)),
            ((x1 - label_w, y0 - label_h - outer, x1, y0 - outer), (x1, y0)),
            ((x1 + outer, cy - label_h / 2, x1 + outer + label_w, cy + label_h / 2), (x1, cy)),
            ((x0 - outer - label_w, cy - label_h / 2, x0 - outer, cy + label_h / 2), (x0, cy)),
            ((x0, y1 + outer, x0 + label_w, y1 + outer + label_h), (x0, y1)),
            ((x1 - label_w, y1 + outer, x1, y1 + outer + label_h), (x1, y1)),
            ((cx - label_w / 2, y0 - label_h - outer, cx + label_w / 2, y0 - outer), (cx, y0)),
            ((cx - label_w / 2, y1 + outer, cx + label_w / 2, y1 + outer + label_h), (cx, y1)),
        ]

        clamped = []
        for rect, anchor in candidates:
            rx0, ry0, rx1, ry1 = rect

            shift_x = 0.0
            shift_y = 0.0

            if rx0 < 0:
                shift_x = -rx0
            elif rx1 > image_w:
                shift_x = image_w - rx1

            if ry0 < 0:
                shift_y = -ry0
            elif ry1 > image_h:
                shift_y = image_h - ry1

            rect2 = (rx0 + shift_x, ry0 + shift_y, rx1 + shift_x, ry1 + shift_y)
            clamped.append((rect2, anchor))

        return clamped

    def _choose_label_placement(
        self,
        draw,
        chunk,
        zoom,
        font,
        placed_label_rects,
        placed_box_rects,
        image_w,
        image_h,
    ):
        label = self._chunk_label(chunk)
        text_w, text_h = self._text_size(draw, label, font)

        pad_x = 4
        pad_y = 2
        label_w = text_w + pad_x * 2
        label_h = text_h + pad_y * 2

        box_rect = self._scale_bbox(chunk.bbox, zoom)
        is_group = chunk.type == "group"
        margin = max(6.0, zoom * 4.0)

        candidates = self._candidate_label_boxes(
            box_rect=box_rect,
            label_w=label_w,
            label_h=label_h,
            margin=margin,
            image_w=image_w,
            image_h=image_h,
            is_group=is_group,
        )

        for rect, anchor in candidates:
            overlaps_label = any(self._rects_overlap(rect, r) for r in placed_label_rects)
            overlaps_box = any(self._rects_overlap(rect, r) for r in placed_box_rects)
            if not overlaps_label and not overlaps_box:
                return rect, anchor, True

        for rect, anchor in candidates:
            overlaps_label = any(self._rects_overlap(rect, r) for r in placed_label_rects)
            if not overlaps_label:
                return rect, anchor, True

        best_rect = None
        best_anchor = None
        best_score = None

        bx0, by0, bx1, by1 = box_rect
        box_cx = (bx0 + bx1) / 2.0
        box_cy = (by0 + by1) / 2.0

        for rect, anchor in candidates:
            score = 0.0

            for other_label in placed_label_rects:
                if self._rects_overlap(rect, other_label):
                    score += 1000.0

            for other_box in placed_box_rects:
                if self._rects_overlap(rect, other_box):
                    score += 300.0

            score += self._point_to_rect_distance_sq(box_cx, box_cy, rect) * 0.001

            if best_score is None or score < best_score:
                best_score = score
                best_rect = rect
                best_anchor = anchor

        return best_rect, best_anchor, True

    def _draw_label_with_connector(
        self,
        draw,
        label_rect,
        label_text,
        color,
        font,
        anchor,
        draw_connector,
    ):
        x0, y0, x1, y1 = label_rect

        draw.rectangle(label_rect, fill=color)

        pad_x = 4
        pad_y = 2
        draw.text((x0 + pad_x, y0 + pad_y), label_text, fill=(255, 255, 255), font=font)

        if draw_connector:
            lx = (x0 + x1) / 2.0
            ly = (y0 + y1) / 2.0
            ax, ay = anchor
            draw.line([(ax, ay), (lx, ly)], fill=self.COLOR_MAP["connector"], width=1)

    def _collect_box_rects_recursive(self, chunk, zoom, out, recurse_groups):
        out.append(self._scale_bbox(chunk.bbox, zoom))
        if recurse_groups and chunk.type == "group":
            for child in chunk.children:
                self._collect_box_rects_recursive(child, zoom, out, recurse_groups)

    def _draw_chunk_recursive(
        self,
        draw,
        chunk,
        zoom,
        font,
        show_labels,
        recurse_groups,
        line_width,
        placed_label_rects,
        placed_box_rects,
        image_w,
        image_h,
    ):
        color = self._chunk_color(chunk)
        x0, y0, x1, y1 = self._scale_bbox(chunk.bbox, zoom)

        draw.rectangle([(x0, y0), (x1, y1)], outline=color, width=line_width)

        if show_labels:
            label_text = self._chunk_label(chunk)
            label_rect, anchor, needs_connector = self._choose_label_placement(
                draw=draw,
                chunk=chunk,
                zoom=zoom,
                font=font,
                placed_label_rects=placed_label_rects,
                placed_box_rects=placed_box_rects,
                image_w=image_w,
                image_h=image_h,
            )

            self._draw_label_with_connector(
                draw=draw,
                label_rect=label_rect,
                label_text=label_text,
                color=color,
                font=font,
                anchor=anchor,
                draw_connector=needs_connector,
            )
            placed_label_rects.append(label_rect)

        if recurse_groups and chunk.type == "group":
            for child in chunk.children:
                self._draw_chunk_recursive(
                    draw=draw,
                    chunk=child,
                    zoom=zoom,
                    font=font,
                    show_labels=show_labels,
                    recurse_groups=recurse_groups,
                    line_width=max(1, line_width - 1),
                    placed_label_rects=placed_label_rects,
                    placed_box_rects=placed_box_rects,
                    image_w=image_w,
                    image_h=image_h,
                )

    def render_page_with_bboxes(
        self,
        page_data: PageChunks,
        output_path: str | Path,
        zoom: float = 2.0,
        show_labels: bool = True,
        recurse_groups: bool = True,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = self.open_pdf()
        try:
            page = self.get_page(doc, page_data.page_number)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)

            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            draw = ImageDraw.Draw(img)
            font = self._get_font(size=max(12, int(12 * zoom / 2)))

            placed_box_rects = []
            for chunk in page_data.chunks:
                self._collect_box_rects_recursive(
                    chunk=chunk,
                    zoom=zoom,
                    out=placed_box_rects,
                    recurse_groups=recurse_groups,
                )

            placed_label_rects = []

            for chunk in page_data.chunks:
                self._draw_chunk_recursive(
                    draw=draw,
                    chunk=chunk,
                    zoom=zoom,
                    font=font,
                    show_labels=show_labels,
                    recurse_groups=recurse_groups,
                    line_width=max(2, int(zoom)),
                    placed_label_rects=placed_label_rects,
                    placed_box_rects=placed_box_rects,
                    image_w=img.width,
                    image_h=img.height,
                )

            img.save(output_path)
            self.log.info("Rendered page %s with overlays to %s", page_data.page_number, output_path)
            return output_path
        finally:
            doc.close()
