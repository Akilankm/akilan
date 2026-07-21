"""Dependency-free schema-version compatibility assessment.

This module classifies artifact schema versions before full structural
validation. It never migrates or mutates an artifact; breaking changes remain
blocked pending an explicit owner-approved migration policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .schema import SUPPORTED_SCHEMA_MAJOR


class SchemaCompatibilityStatus(str, Enum):
    """Stable compatibility outcomes for downstream intake gates."""

    COMPATIBLE = "compatible"
    INVALID = "invalid"
    UNSUPPORTED_MAJOR = "unsupported_major"


@dataclass(frozen=True, order=True, slots=True)
class SchemaVersion:
    """A strict ``major.minor.patch`` artifact schema version."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class SchemaCompatibilityReport:
    """Machine-readable compatibility evidence for one schema version."""

    raw_version: Any
    parsed_version: SchemaVersion | None
    supported_major: int
    status: SchemaCompatibilityStatus
    message: str

    @property
    def compatible(self) -> bool:
        return self.status is SchemaCompatibilityStatus.COMPATIBLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_version": self.raw_version,
            "parsed_version": None if self.parsed_version is None else str(self.parsed_version),
            "supported_major": self.supported_major,
            "status": self.status.value,
            "compatible": self.compatible,
            "message": self.message,
        }


def parse_schema_version(value: Any) -> SchemaVersion:
    """Parse a strict non-negative ``major.minor.patch`` version.

    Boolean values, prefixes, suffixes, omitted components, whitespace, and
    negative components are rejected so consumers never guess compatibility.
    """

    if not isinstance(value, str) or not value:
        raise ValueError("schema version must be a non-empty string")
    if value != value.strip():
        raise ValueError("schema version must not contain surrounding whitespace")

    parts = value.split(".")
    if len(parts) != 3:
        raise ValueError("schema version must use major.minor.patch format")
    if any(not part.isascii() or not part.isdigit() for part in parts):
        raise ValueError("schema version components must be ASCII non-negative integers")

    major, minor, patch = (int(part) for part in parts)
    return SchemaVersion(major=major, minor=minor, patch=patch)


def assess_schema_compatibility(
    value: Any,
    *,
    supported_major: int = SUPPORTED_SCHEMA_MAJOR,
) -> SchemaCompatibilityReport:
    """Classify whether ``value`` is safe for this artifact consumer.

    Compatibility is deliberately major-version based. Minor and patch
    versions are additive or clarifying under the documented schema policy.
    This function does not imply that structural validation has passed.
    """

    if not isinstance(supported_major, int) or isinstance(supported_major, bool) or supported_major < 0:
        raise ValueError("supported_major must be a non-negative integer")

    try:
        parsed = parse_schema_version(value)
    except ValueError as exc:
        return SchemaCompatibilityReport(
            raw_version=value,
            parsed_version=None,
            supported_major=supported_major,
            status=SchemaCompatibilityStatus.INVALID,
            message=str(exc),
        )

    if parsed.major != supported_major:
        return SchemaCompatibilityReport(
            raw_version=value,
            parsed_version=parsed,
            supported_major=supported_major,
            status=SchemaCompatibilityStatus.UNSUPPORTED_MAJOR,
            message=f"unsupported schema major {parsed.major}; expected {supported_major}.x.x",
        )

    return SchemaCompatibilityReport(
        raw_version=value,
        parsed_version=parsed,
        supported_major=supported_major,
        status=SchemaCompatibilityStatus.COMPATIBLE,
        message="schema major is supported; run structural validation before consumption",
    )
