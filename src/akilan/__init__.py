"""AKILAN: geometry-aware PDF artifact construction with PyMuPDF."""

from .api import build_artifact
from .config import ExtractionConfig
from .extraction import PDFArtifactBuilder, PDFExtractionError
from .geometry import BBox
from .models import DocumentArtifact, PageArtifact
from .version import __version__

__all__ = [
    "BBox",
    "DocumentArtifact",
    "ExtractionConfig",
    "PDFArtifactBuilder",
    "PDFExtractionError",
    "PageArtifact",
    "build_artifact",
    "__version__",
]
