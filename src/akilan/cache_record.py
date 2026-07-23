"""Operational completeness records for safe artifact cache reuse."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifact_directory import validate_artifact_directory
from .artifact_loader import load_artifact_directory
from .cache_identity import ArtifactCacheIdentity, build_artifact_cache_identity
from .config import ExtractionConfig
from .serialization import dump_json

CACHE_RECORD_NAME = ".akilan-cache.json"
CACHE_RECORD_VERSION = "1"


@dataclass(frozen=True, slots=True)
class ArtifactCacheValidation:
    """Read-only decision describing whether an artifact is safe to reuse."""

    hit: bool
    identity: ArtifactCacheIdentity
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "hit": self.hit,
            "identity": self.identity.to_dict(),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class ArtifactCacheResolution:
    """Validated cache decision with the canonical document payload on a hit."""

    validation: ArtifactCacheValidation
    artifact: dict[str, Any] | None

    @property
    def hit(self) -> bool:
        """Return whether a complete identity-equivalent artifact was loaded."""

        return self.validation.hit and self.artifact is not None

    @property
    def reasons(self) -> tuple[str, ...]:
        """Expose deterministic cache-miss reasons."""

        return self.validation.reasons


def write_artifact_cache_record(
    artifact_dir: str | Path,
    identity: ArtifactCacheIdentity,
) -> Path:
    """Write the completion record inside an unpublished staging directory."""

    root = Path(artifact_dir).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    path = root / CACHE_RECORD_NAME
    dump_json(
        path,
        {
            "record_version": CACHE_RECORD_VERSION,
            "state": "complete",
            "identity": identity.to_dict(),
        },
    )
    return path


def validate_artifact_cache(
    pdf_path: str | Path,
    artifact_dir: str | Path,
    config: ExtractionConfig | None = None,
) -> ArtifactCacheValidation:
    """Return whether a persisted artifact is complete and identity-equivalent."""

    identity = build_artifact_cache_identity(pdf_path, config)
    root = Path(artifact_dir).expanduser().resolve()
    reasons: list[str] = []
    record_path = root / CACHE_RECORD_NAME

    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        reasons.append("cache completion record is missing")
        record = None
    except OSError as exc:
        reasons.append(f"cache completion record cannot be read: {exc}")
        record = None
    except json.JSONDecodeError as exc:
        reasons.append(
            f"cache completion record contains invalid JSON at line {exc.lineno}, column {exc.colno}"
        )
        record = None

    if isinstance(record, dict):
        if record.get("record_version") != CACHE_RECORD_VERSION:
            reasons.append("cache completion record version is unsupported")
        if record.get("state") != "complete":
            reasons.append("cache completion record does not declare a complete artifact")
        recorded_identity = record.get("identity")
        if recorded_identity != identity.to_dict():
            reasons.append("cache identity does not match the current extraction request")
    elif record is not None:
        reasons.append("cache completion record must contain a JSON object")

    violations = validate_artifact_directory(root, raise_on_error=False)
    if violations:
        reasons.append(f"artifact directory validation failed with {len(violations)} violation(s)")

    return ArtifactCacheValidation(
        hit=not reasons,
        identity=identity,
        reasons=tuple(reasons),
    )


def resolve_artifact_cache(
    pdf_path: str | Path,
    artifact_dir: str | Path,
    config: ExtractionConfig | None = None,
) -> ArtifactCacheResolution:
    """Load the canonical artifact only after a complete cache hit is proven.

    Cache misses are normal control flow and return ``artifact=None`` with stable
    reasons. The artifact directory is validated twice: once for the cache
    decision and again immediately before loading. This closes the race where a
    directory changes between validation and consumption.
    """

    validation = validate_artifact_cache(pdf_path, artifact_dir, config)
    if not validation.hit:
        return ArtifactCacheResolution(validation=validation, artifact=None)

    try:
        artifact = load_artifact_directory(artifact_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        failed_validation = ArtifactCacheValidation(
            hit=False,
            identity=validation.identity,
            reasons=(f"validated cache could not be loaded safely: {exc}",),
        )
        return ArtifactCacheResolution(validation=failed_validation, artifact=None)

    return ArtifactCacheResolution(validation=validation, artifact=artifact)
