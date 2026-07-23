"""Native page-level extractors."""

from .graphics import extract_drawings
from .images import extract_images
from .interactive import extract_annotations, extract_links, extract_widgets
from .tables import extract_tables
from .text import extract_text_blocks

__all__ = [
    "extract_annotations",
    "extract_drawings",
    "extract_images",
    "extract_links",
    "extract_tables",
    "extract_text_blocks",
    "extract_widgets",
]
