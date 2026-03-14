from __future__ import annotations

from typing import Optional

from .atoms import PdfAtomExtractor
from .base import BasePdfComponent
from .layout_tree import LayoutTreeBuilder
from .models import BBox, PageChunks


class PdfPageParser(BasePdfComponent):
    def __init__(self, pdf_path: Optional[str] = None):
        super().__init__(pdf_path=pdf_path, component="page_parser")
        self.atom_extractor = PdfAtomExtractor(pdf_path=pdf_path)

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
        rect = page.rect

        atoms = self.atom_extractor.extract_page_atoms(
            page=page,
            page_number=page_number,
            include_table_base64=include_table_base64,
            include_image_base64=include_image_base64,
            skip_background_images=skip_background_images,
        )

        debug = {
            "atom_count": len(atoms),
            "text_atom_count": sum(1 for a in atoms if a.type == "text"),
            "image_atom_count": sum(1 for a in atoms if a.type == "image"),
            "table_atom_count": sum(1 for a in atoms if a.type == "table"),
        }

        if enable_grouping and atoms:
            builder = LayoutTreeBuilder(
                page_number=page_number,
                page_width=float(rect.width),
                page_height=float(rect.height),
            )
            page_bbox = BBox(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))
            chunks = builder.build(atoms, page_bbox)
        else:
            chunks = atoms
            for idx, chunk in enumerate(chunks):
                chunk.chunk_index = idx

        return PageChunks(
            page_number=page_number,
            width=float(rect.width),
            height=float(rect.height),
            chunks=chunks,
            debug=debug,
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
