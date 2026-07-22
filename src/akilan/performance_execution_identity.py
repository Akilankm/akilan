"""Deterministic execution-context identity for performance evidence."""

from __future__ import annotations

import platform
from dataclasses import asdict, dataclass
from typing import Any

import fitz

from .canonical_json import canonical_json_fingerprint
from .config import ExtractionConfig
from .version import __version__


@dataclass(frozen=True, slots=True)
class PerformanceExecutionIdentity:
    """Exact runtime and extraction context used for a performance run."""

    python_implementation: str
    python_version: str
    platform_system: str
    platform_machine: str
    pymupdf_version: str
    akilan_version: str
    extraction_config: dict[str, Any]
    fingerprint: str

    def payload(self) -> dict[str, Any]:
        """Return the canonical content protected by the fingerprint."""

        return {
            "python_implementation": self.python_implementation,
            "python_version": self.python_version,
            "platform_system": self.platform_system,
            "platform_machine": self.platform_machine,
            "pymupdf_version": self.pymupdf_version,
            "akilan_version": self.akilan_version,
            "extraction_config": self.extraction_config,
        }

    @property
    def valid(self) -> bool:
        """Return whether the fingerprint matches the represented context."""

        return self.fingerprint == canonical_json_fingerprint(self.payload())

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic machine-readable identity evidence."""

        return {**asdict(self), "valid": self.valid}


def build_performance_execution_identity(
    config: ExtractionConfig | None = None,
) -> PerformanceExecutionIdentity:
    """Build an immutable identity for reproducible performance comparison.

    The fingerprint binds performance evidence to the interpreter, operating
    system family, machine architecture, PyMuPDF and AKILAN versions, and the
    complete validated extraction configuration. Volatile host details such as
    hostname, process identifier, and timestamps are intentionally excluded.
    """

    effective_config = config or ExtractionConfig()
    effective_config.validate()
    config_payload = asdict(effective_config)
    payload = {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "pymupdf_version": fitz.VersionBind,
        "akilan_version": __version__,
        "extraction_config": config_payload,
    }
    return PerformanceExecutionIdentity(
        **payload,
        fingerprint=canonical_json_fingerprint(payload),
    )


def assess_performance_execution_identity_match(
    baseline: PerformanceExecutionIdentity,
    current: PerformanceExecutionIdentity,
) -> bool:
    """Return whether two valid runs share the exact execution context."""

    return baseline.valid and current.valid and baseline.fingerprint == current.fingerprint
