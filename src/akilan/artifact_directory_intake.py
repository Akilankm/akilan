"""Combined byte-integrity, compatibility, and structural artifact intake."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifact_directory_integrity import (
    ArtifactDirectoryIntegrityReport,
    assess_artifact_directory_integrity,
)
from .artifact_intake import ArtifactIntakeReport, assess_artifact_intake


@dataclass(frozen=True, slots=True)
class ArtifactDirectoryIntakeReport:
    """Deterministic all-or-nothing evidence for a persisted artifact directory."""

    integrity: ArtifactDirectoryIntegrityReport
    intake: ArtifactIntakeReport | None
    status: str
    message: str

    @property
    def accepted(self) -> bool:
        """Return whether the complete directory and canonical document are safe to consume."""

        return self.integrity.accepted and self.intake is not None and self.intake.accepted

    def to_dict(self) -> dict[str, Any]:
        """Serialize stable machine-readable intake evidence."""

        return {
            "accepted": self.accepted,
            "status": self.status,
            "message": self.message,
            "integrity": self.integrity.to_dict(),
            "intake": None if self.intake is None else self.intake.to_dict(),
        }


def _document_identity(report: ArtifactDirectoryIntegrityReport) -> tuple[str, int]:
    for entry in report.files:
        if entry.relative_path == "document.json":
            return entry.sha256, entry.size_bytes
    raise RuntimeError("accepted integrity report omitted document.json")


def assess_artifact_directory_intake(
    artifact_root: str | Path,
) -> ArtifactDirectoryIntakeReport:
    """Assess complete persisted bytes before compatibility and structural intake.

    Directory integrity runs first and fails closed. The canonical ``document.json`` is
    then read once for decoding and parsing, and its bytes must still match the accepted
    inventory. The function never repairs, migrates, or mutates artifact files.
    """

    integrity = assess_artifact_directory_integrity(artifact_root)
    if not integrity.accepted:
        return ArtifactDirectoryIntakeReport(
            integrity=integrity,
            intake=None,
            status="integrity_rejected",
            message="artifact directory failed complete byte-integrity assessment",
        )

    document_path = Path(integrity.root_path) / "document.json"
    try:
        raw = document_path.read_bytes()
    except OSError:
        return ArtifactDirectoryIntakeReport(
            integrity=integrity,
            intake=None,
            status="changed_after_integrity",
            message="artifact document.json changed after integrity assessment",
        )

    expected_sha256, expected_size = _document_identity(integrity)
    if len(raw) != expected_size or hashlib.sha256(raw).hexdigest() != expected_sha256:
        return ArtifactDirectoryIntakeReport(
            integrity=integrity,
            intake=None,
            status="changed_after_integrity",
            message="artifact document.json changed after integrity assessment",
        )

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return ArtifactDirectoryIntakeReport(
            integrity=integrity,
            intake=None,
            status="invalid_document_json",
            message="artifact document.json could not be decoded as JSON",
        )

    if not isinstance(payload, dict):
        return ArtifactDirectoryIntakeReport(
            integrity=integrity,
            intake=None,
            status="invalid_document_root",
            message="artifact document.json root must be an object",
        )

    intake = assess_artifact_intake(payload)
    if not intake.accepted:
        return ArtifactDirectoryIntakeReport(
            integrity=integrity,
            intake=intake,
            status="artifact_rejected",
            message="artifact is incompatible or structurally invalid",
        )

    return ArtifactDirectoryIntakeReport(
        integrity=integrity,
        intake=intake,
        status="accepted",
        message="artifact directory is byte-complete, compatible, and structurally valid",
    )
