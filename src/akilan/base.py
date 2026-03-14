from __future__ import annotations

import base64
from typing import Optional

import fitz

from .logger import get_logger
from .models import BBox


class BasePdfComponent:
    def __init__(self, pdf_path: Optional[str], component: str):
        if not pdf_path:
            raise ValueError("pdf_path must be provided")

        self.pdf_path = pdf_path
        self.log = get_logger(component=component, pdf_path=pdf_path)
        self.log.info("%s initialized", self.__class__.__name__)

    def open_pdf(self):
        self.log.info("Opening PDF")
        doc = fitz.open(self.pdf_path)
        self.log.info("PDF loaded successfully with %s pages", len(doc))
        return doc

    def validate_page_number(self, page_number: int, total_pages: int) -> None:
        if page_number < 1 or page_number > total_pages:
            raise ValueError(f"page_number must be between 1 and {total_pages}")

    def get_page(self, doc, page_number: int):
        self.validate_page_number(page_number, len(doc))
        return doc[page_number - 1]

    def bbox_from_tuple(self, bbox) -> BBox:
        x0, y0, x1, y1 = bbox
        return BBox(float(x0), float(y0), float(x1), float(y1))

    def rect_from_bbox(self, bbox: BBox) -> fitz.Rect:
        return fitz.Rect(bbox.x0, bbox.y0, bbox.x1, bbox.y1)

    def render_bbox_to_base64(
        self,
        page,
        bbox: BBox,
        zoom: float = 2.0,
        padding: float = 0.0,
    ) -> str:
        rect = self.rect_from_bbox(bbox)
        if padding:
            rect = fitz.Rect(
                rect.x0 - padding,
                rect.y0 - padding,
                rect.x1 + padding,
                rect.y1 + padding,
            )

        pix = page.get_pixmap(
            matrix=fitz.Matrix(zoom, zoom),
            clip=rect,
            alpha=False,
        )
        return base64.b64encode(pix.tobytes("png")).decode("utf-8")
