"""Combined byte-integrity, compatibility, and structural artifact intake."""

from __future__ import annotations

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


def assess_artifact_directory_intake(
    artifact_root: str | Path,
) -> ArtifactDirectoryIntakeReport:
    """Assess complete persisted bytes before compatibility and structural intake.

    Directory integrity runs first and fails closed. The canonical ``document.json`` is
    decoded and parsed only after the complete regular-file inventory is accepted. The
    function is read-only and never repairs, migrates, or mutates artifact files.
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
        payload = json.loads(document_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ArtifactDirectoryIntakeReport(
            integrity=integrity,
            intake=None,
            status="invalid_document_json",
            message="artifact document.json could not be decoded as a JSON object",
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
