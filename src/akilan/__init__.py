"""AKILAN: geometry-aware PDF artifact construction with PyMuPDF."""

from .api import build_artifact
from .artifact_directory import validate_artifact_directory
from .artifact_integrity import validate_page_identities
from .artifact_loader import load_artifact_directory
from .benchmark_acceptance import (
    BenchmarkAcceptanceReport,
    BenchmarkThresholds,
    BenchmarkViolation,
    evaluate_corpus,
    write_benchmark_acceptance_report,
)
from .benchmark_cache_validation import (
    BenchmarkCacheViolation,
    validate_benchmark_cache_entry,
)
from .build_profile import ArtifactOperationProfile
from .cache_identity import ArtifactCacheIdentity, build_artifact_cache_identity
from .cache_orchestration import ArtifactBuildResolution, build_or_resolve_artifact
from .cache_record import (
    ArtifactCacheResolution,
    ArtifactCacheValidation,
    resolve_artifact_cache,
    validate_artifact_cache,
)
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
from .page_selection import PageSelectionError, parse_page_selection
from .persisted_graph_validation import (
    PersistedGraphViolation,
    find_persisted_graph_violations,
)
from .relationship_validation import (
    DuplicateFootnoteMarker,
    find_duplicate_footnote_markers,
)
from .schema import ArtifactSchemaError, SchemaViolation, validate_artifact
from .schema_compatibility import (
    SchemaCompatibilityReport,
    SchemaCompatibilityStatus,
    SchemaVersion,
    assess_schema_compatibility,
    parse_schema_version,
)
from .schema_resource import load_artifact_json_schema
from .version import __version__

__all__ = [
    "ArtifactBuildResolution",
    "ArtifactCacheIdentity",
    "ArtifactCacheResolution",
    "ArtifactCacheValidation",
    "ArtifactOperationProfile",
    "ArtifactSchemaError",
    "BBox",
    "BenchmarkAcceptanceReport",
    "BenchmarkCacheViolation",
    "BenchmarkThresholds",
    "BenchmarkViolation",
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
    "PageSelectionError",
    "PersistedGraphViolation",
    "SchemaCompatibilityReport",
    "SchemaCompatibilityStatus",
    "SchemaVersion",
    "SchemaViolation",
    "__version__",
    "assess_schema_compatibility",
    "build_artifact",
    "build_artifact_cache_identity",
    "build_or_resolve_artifact",
    "evaluate_corpus",
    "find_duplicate_element_ids",
    "find_duplicate_footnote_markers",
    "find_persisted_graph_violations",
    "load_artifact_directory",
    "load_artifact_json_schema",
    "load_corpus_sources",
    "parse_page_selection",
    "parse_schema_version",
    "resolve_artifact_cache",
    "sync_corpus",
    "validate_artifact",
    "validate_artifact_cache",
    "validate_artifact_directory",
    "validate_benchmark_cache_entry",
    "validate_manifest",
    "validate_page_identities",
    "verify_corpus",
    "write_benchmark_acceptance_report",
]
