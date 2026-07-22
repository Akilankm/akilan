"""Deterministic all-or-nothing intake for persisted artifact directories."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifact_directory_intake import (
    ArtifactDirectoryIntakeReport,
    assess_artifact_directory_intake,
)
from .canonical_json import canonical_json_fingerprint


@dataclass(frozen=True, slots=True)
class ArtifactDirectoryBatchIntakeEntry:
    """Intake evidence for one caller-identified persisted artifact directory."""

    identifier: str
    root_path: str
    report: ArtifactDirectoryIntakeReport

    @property
    def accepted(self) -> bool:
        """Return whether this directory passed complete intake."""

        return self.report.accepted

    def to_dict(self) -> dict[str, Any]:
        """Serialize stable machine-readable entry evidence."""

        return {
            "identifier": self.identifier,
            "root_path": self.root_path,
            "accepted": self.accepted,
            "report": self.report.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ArtifactDirectoryBatchIntakeReport:
    """Deterministic all-or-nothing evidence for an artifact directory set."""

    entries: tuple[ArtifactDirectoryBatchIntakeEntry, ...]
    status: str
    message: str
    fingerprint: str

    @property
    def total_count(self) -> int:
        """Return the number of assessed artifact directories."""

        return len(self.entries)

    @property
    def accepted_count(self) -> int:
        """Return the number of accepted directories."""

        return sum(entry.accepted for entry in self.entries)

    @property
    def rejected_count(self) -> int:
        """Return the number of rejected directories."""

        return self.total_count - self.accepted_count

    @property
    def accepted(self) -> bool:
        """Return whether a non-empty set passed intake completely."""

        return self.total_count > 0 and self.rejected_count == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize stable machine-readable batch evidence."""

        return {
            "accepted": self.accepted,
            "status": self.status,
            "message": self.message,
            "total_count": self.total_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "fingerprint": self.fingerprint,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def assess_artifact_directory_batch_intake(
    artifact_roots: Mapping[str, str | Path],
) -> ArtifactDirectoryBatchIntakeReport:
    """Assess an exact caller-identified set of persisted artifact directories.

    Identifiers are validated and ordered lexicographically. Every directory is assessed,
    preserving complete rejection evidence while preventing a valid subset from being
    mistaken for an accepted batch. No artifact bytes are modified.
    """

    invalid_ids = [
        identifier
        for identifier in artifact_roots
        if not isinstance(identifier, str) or not identifier
    ]
    if invalid_ids:
        raise ValueError("artifact directory identifiers must be non-empty strings")

    normalized = tuple(
        (
            identifier,
            Path(artifact_roots[identifier]).expanduser().resolve(strict=False),
        )
        for identifier in sorted(artifact_roots)
    )
    entries = tuple(
        ArtifactDirectoryBatchIntakeEntry(
            identifier=identifier,
            root_path=str(root),
            report=assess_artifact_directory_intake(root),
        )
        for identifier, root in normalized
    )

    if not entries:
        status = "empty_batch"
        message = "artifact directory batch is empty"
    elif any(not entry.accepted for entry in entries):
        status = "rejected"
        message = "one or more artifact directories failed intake"
    else:
        status = "accepted"
        message = "all artifact directories passed byte-integrity and semantic intake"

    evidence = [entry.to_dict() for entry in entries]
    return ArtifactDirectoryBatchIntakeReport(
        entries=entries,
        status=status,
        message=message,
        fingerprint=canonical_json_fingerprint(evidence),
    )
