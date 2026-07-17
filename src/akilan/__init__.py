"""AKILAN: geometry-aware PDF artifact construction with PyMuPDF."""

from .api import build_artifact
from .config import ExtractionConfig
from .extraction import PDFArtifactBuilder, PDFExtractionError
from .geometry import BBox
from .models import DocumentArtifact, PageArtifact
from .schema import ArtifactSchemaError, SchemaViolation, validate_artifact
from .version import __version__

__all__ = [
    "ArtifactSchemaError",
    "BBox",
    "DocumentArtifact",
    "ExtractionConfig",
    "PDFArtifactBuilder",
    "PDFExtractionError",
    "PageArtifact",
    "SchemaViolation",
    "__version__",
    "build_artifact",
    "validate_artifact",
]
