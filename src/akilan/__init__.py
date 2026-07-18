"""AKILAN: geometry-aware PDF artifact construction with PyMuPDF."""

from .api import build_artifact
from .artifact_directory import validate_artifact_directory
from .artifact_integrity import validate_page_identities
from .config import ExtractionConfig
from .corpus import (
    CorpusDownload,
    CorpusSource,
    CorpusSourceError,
    CorpusVerification,
    load_corpus_sources,
    sync_corpus,
    verify_corpus,
)
from .extraction import PDFArtifactBuilder, PDFExtractionError
from .geometry import BBox
from .manifest_schema import validate_manifest
from .models import DocumentArtifact, PageArtifact
from .schema import ArtifactSchemaError, SchemaViolation, validate_artifact
from .schema_resource import load_artifact_json_schema
from .version import __version__

__all__ = [
    "ArtifactSchemaError",
    "BBox",
    "CorpusDownload",
    "CorpusSource",
    "CorpusSourceError",
    "CorpusVerification",
    "DocumentArtifact",
    "ExtractionConfig",
    "PDFArtifactBuilder",
    "PDFExtractionError",
    "PageArtifact",
    "SchemaViolation",
    "__version__",
    "build_artifact",
    "load_artifact_json_schema",
    "load_corpus_sources",
    "sync_corpus",
    "validate_artifact",
    "validate_artifact_directory",
    "validate_manifest",
    "validate_page_identities",
    "verify_corpus",
]
