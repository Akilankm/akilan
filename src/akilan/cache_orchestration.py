"""Cache-aware artifact construction with validated reuse."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .builder import PDFArtifactBuilder, PDFExtractionError
from .cache_identity import ArtifactCacheIdentity
from .cache_record import resolve_artifact_cache
from .config import ExtractionConfig


@dataclass(frozen=True, slots=True)
class ArtifactBuildResolution:
    """Canonical artifact payload plus deterministic reuse evidence."""

    artifact: dict[str, Any]
    cache_hit: bool
    identity: ArtifactCacheIdentity
    prior_miss_reasons: tuple[str, ...]

    @property
    def rebuilt(self) -> bool:
        """Return whether this call produced and validated a fresh artifact."""

        return not self.cache_hit

    def to_dict(self) -> dict[str, Any]:
        """Return stable operational evidence without duplicating the artifact payload."""

        return {
            "cache_hit": self.cache_hit,
            "rebuilt": self.rebuilt,
            "identity": self.identity.to_dict(),
            "prior_miss_reasons": list(self.prior_miss_reasons),
        }


def build_or_resolve_artifact(
    pdf_path: str | Path,
    output_dir: str | Path,
    config: ExtractionConfig | None = None,
    *,
    password: str | None = None,
) -> ArtifactBuildResolution:
    """Reuse a complete equivalent artifact or build and validate a replacement.

    The function never trusts directory presence alone. It first performs the full
    cache validation boundary. On a miss, it delegates publication to
    :class:`PDFArtifactBuilder`, then resolves the freshly published directory
    through the same validation and loading boundary before returning it.

    Existing non-equivalent output remains protected by ``ExtractionConfig.overwrite``;
    callers must opt into replacement exactly as they do with ``PDFArtifactBuilder``.
    """

    effective_config = config or ExtractionConfig()
    initial = resolve_artifact_cache(pdf_path, output_dir, effective_config)
    if initial.hit and initial.artifact is not None:
        return ArtifactBuildResolution(
            artifact=initial.artifact,
            cache_hit=True,
            identity=initial.validation.identity,
            prior_miss_reasons=(),
        )

    PDFArtifactBuilder(effective_config).build(pdf_path, output_dir, password=password)
    refreshed = resolve_artifact_cache(pdf_path, output_dir, effective_config)
    if not refreshed.hit or refreshed.artifact is None:
        reasons = "; ".join(refreshed.reasons) or "unknown validation failure"
        raise PDFExtractionError(f"Freshly built artifact could not be resolved safely: {reasons}")

    return ArtifactBuildResolution(
        artifact=refreshed.artifact,
        cache_hit=False,
        identity=refreshed.validation.identity,
        prior_miss_reasons=initial.reasons,
    )
