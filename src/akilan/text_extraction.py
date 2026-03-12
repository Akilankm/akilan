import fitz
from typing import Optional
from .logger import get_logger


class PdfTextExtractor:
    def __init__(self, pdf_path: Optional[str] = None):
        if not pdf_path:
            raise ValueError("pdf_path must be provided")

        self.pdf_path = pdf_path
        self.log = get_logger(
            component="text_extraction",
            pdf_path=self.pdf_path,
        )

        self.log.info("PdfTextExtractor initialized")

    def open_pdf(self):
        self.log.info("Opening PDF")
        doc = fitz.open(self.pdf_path)
        self.log.info(f"PDF loaded successfully with {len(doc)} pages")
        return doc

    def _validate_page_number(self, page_number: int, total_pages: int) -> None:
        if page_number < 1 or page_number > total_pages:
            self.log.error(
                f"Invalid page number: {page_number}. PDF has {total_pages} pages"
            )
            raise ValueError(f"page_number must be between 1 and {total_pages}")

    def _get_page(self, doc, page_number: int):
        total_pages = len(doc)
        self._validate_page_number(page_number, total_pages)
        return doc[page_number - 1]

    def _get_text_blocks(self, page) -> list[dict]:
        """
        Extract only text blocks from the page dict.
        """
        page_dict = page.get_text("dict")
        raw_blocks = page_dict.get("blocks", [])

        text_blocks = []
        for block in raw_blocks:
            if block.get("type") == 0:
                text_blocks.append(block)

        return text_blocks

    def _build_block_text(self, block: dict) -> str:
        """
        Reconstruct a block's text from its lines and spans.
        """
        lines = []

        for line in block.get("lines", []):
            line_parts = []

            for span in line.get("spans", []):
                span_text = span.get("text", "")
                if span_text:
                    line_parts.append(span_text)

            line_text = "".join(line_parts).strip()
            if line_text:
                lines.append(line_text)

        return "\n".join(lines).strip()

    def _sort_blocks(self, blocks: list[dict]) -> list[dict]:
        """
        Sort blocks top-to-bottom, then left-to-right.
        """
        return sorted(
            blocks,
            key=lambda block: (
                block["bbox"]["y0"],
                block["bbox"]["x0"],
            ),
        )

    def extract_page_blocks(self, page_number: int) -> list[dict]:
        """
        Extract structured text blocks from a single page.
        """
        self.log.info(f"Starting block extraction for page_number={page_number}")

        doc = self.open_pdf()

        try:
            page = self._get_page(doc, page_number)
            raw_text_blocks = self._get_text_blocks(page)

            processed_blocks = []

            for block in raw_text_blocks:
                bbox = block.get("bbox", (0, 0, 0, 0))
                x0, y0, x1, y1 = bbox

                block_text = self._build_block_text(block)
                if not block_text:
                    continue

                processed_blocks.append(
                    {
                        "bbox": {
                            "x0": x0,
                            "y0": y0,
                            "x1": x1,
                            "y1": y1,
                        },
                        "text": block_text,
                    }
                )

            ordered_blocks = self._sort_blocks(processed_blocks)

            result = []
            for index, block in enumerate(ordered_blocks):
                result.append(
                    {
                        "block_index": index,
                        "page_number": page_number,
                        "bbox": block["bbox"],
                        "text": block["text"],
                    }
                )

            self.log.info(
                f"Extracted {len(result)} text blocks from page {page_number}"
            )
            return result

        finally:
            doc.close()
            self.log.info("PDF closed after block extraction")

    def extract_page_text(self, page_number: int) -> str:
        """
        Extract full page text by joining blocks in reading order.
        """
        self.log.info(f"Starting page text extraction for page_number={page_number}")

        blocks = self.extract_page_blocks(page_number)
        page_text = "\n\n".join(block["text"] for block in blocks)

        self.log.info(f"Successfully extracted text from page {page_number}")
        return page_text