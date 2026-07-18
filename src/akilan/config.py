"""Configuration models for deterministic PDF artifact extraction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExtractionConfig:
    """Controls which native PyMuPDF signals are captured.

    Defaults favor a complete AI-facing artifact while avoiding character-level
    payload explosion and high-resolution page rendering. ``page_numbers`` uses
    one-based source page numbers and preserves their original identities.
    """

    extract_text: bool = True
    include_characters: bool = False
    extract_tables: bool = True
    extract_images: bool = True
    extract_drawings: bool = True
    extract_links: bool = True
    extract_annotations: bool = True
    extract_widgets: bool = True
    render_pages: bool = False
    render_dpi: int = 144
    include_page_markdown: bool = True
    include_document_markdown: bool = True
    include_plain_text: bool = True
    suppress_table_text_in_reading_order: bool = True
    header_ratio: float = 0.08
    footer_ratio: float = 0.08
    repeated_margin_min_pages: int = 2
    repeated_margin_min_fraction: float = 0.30
    min_image_width: float = 8.0
    min_image_height: float = 8.0
    min_drawing_area: float = 1.0
    page_numbers: tuple[int, ...] | None = None
    overwrite: bool = False

    def validate(self) -> None:
        if not 36 <= self.render_dpi <= 600:
            raise ValueError("render_dpi must be between 36 and 600")
        for name in ("header_ratio", "footer_ratio"):
            value = getattr(self, name)
            if not 0 <= value < 0.5:
                raise ValueError(f"{name} must be in [0, 0.5)")
        if self.repeated_margin_min_pages < 2:
            raise ValueError("repeated_margin_min_pages must be >= 2")
        if not 0 < self.repeated_margin_min_fraction <= 1:
            raise ValueError("repeated_margin_min_fraction must be in (0, 1]")
        if self.page_numbers is not None:
            if not self.page_numbers:
                raise ValueError("page_numbers must contain at least one page")
            if any(not isinstance(page, int) or isinstance(page, bool) or page < 1 for page in self.page_numbers):
                raise ValueError("page_numbers must contain positive one-based integers")
            if len(set(self.page_numbers)) != len(self.page_numbers):
                raise ValueError("page_numbers must not contain duplicates")
            if tuple(sorted(self.page_numbers)) != self.page_numbers:
                raise ValueError("page_numbers must be in ascending source order")
