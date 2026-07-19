"""AKILAN: geometry-aware PDF artifact construction with PyMuPDF."""

from .api import build_artifact
from .artifact_directory import validate_artifact_directory
from .artifact_integrity import validate_page_identities
from .artifact_loader import load_artifact_directory
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
from .element_identity import (
    DuplicateElementIdentity,
    ElementIdentityOccurrence,
    find_duplicate_element_ids,
)
from .extraction import PDFArtifactBuilder, PDFExtractionError
from .geometry import BBox
from .manifest_schema import validate_manifest
from .models import DocumentArtifact, PageArtifact
from .persisted_graph_validation import (
    PersistedGraphViolation,
    find_persisted_graph_violations,
)
from .relationship_validation import (
    DuplicateFootnoteMarker,
    find_duplicate_footnote_markers,
)
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
    "DuplicateElementIdentity",
    "DuplicateFootnoteMarker",
    "ElementIdentityOccurrence",
    "ExtractionConfig",
    "PDFArtifactBuilder",
    "PDFExtractionError",
    "PageArtifact",
    "PersistedGraphViolation",
    "SchemaViolation",
    "__version__",
    "build_artifact",
    "find_duplicate_element_ids",
    "find_duplicate_footnote_markers",
    "find_persisted_graph_violations",
    "load_artifact_directory",
    "load_artifact_json_schema",
    "load_corpus_sources",
    "sync_corpus",
    "validate_artifact",
    "validate_artifact_directory",
    "validate_manifest",
    "validate_page_identities",
    "verify_corpus",
]
