"""Deterministic fail-closed intake for an exact set of artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .artifact_intake import ArtifactIntakeReport, assess_artifact_intake
from .canonical_json import canonical_json_fingerprint


@dataclass(frozen=True, slots=True)
class ArtifactBatchIntakeEntry:
    """Intake evidence for one caller-identified artifact."""

    artifact_id: str
    report: ArtifactIntakeReport

    def to_dict(self) -> dict[str, Any]:
        """Serialize stable entry evidence."""

        return {
            "artifact_id": self.artifact_id,
            **self.report.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ArtifactBatchIntakeReport:
    """Deterministic evidence for one all-or-nothing artifact-set decision."""

    entries: tuple[ArtifactBatchIntakeEntry, ...]
    fingerprint: str

    @property
    def total_count(self) -> int:
        return len(self.entries)

    @property
    def accepted_count(self) -> int:
        return sum(entry.report.accepted for entry in self.entries)

    @property
    def rejected_count(self) -> int:
        return self.total_count - self.accepted_count

    @property
    def accepted(self) -> bool:
        """Return whether the non-empty exact artifact set is fully acceptable."""

        return self.total_count > 0 and self.rejected_count == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize stable, machine-readable batch evidence."""

        return {
            "accepted": self.accepted,
            "total_count": self.total_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "fingerprint": self.fingerprint,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def assess_artifact_batch_intake(
    artifacts: Mapping[str, Mapping[str, Any]],
) -> ArtifactBatchIntakeReport:
    """Assess an exact artifact set without mutating or migrating any member.

    Caller-provided identifiers are normalized only by requiring non-empty strings.
    Entries are evaluated and emitted in lexicographical identifier order. The batch
    fails closed when empty or when any member is incompatible or structurally invalid.
    """

    invalid_ids = [
        artifact_id
        for artifact_id in artifacts
        if not isinstance(artifact_id, str) or not artifact_id
    ]
    if invalid_ids:
        raise ValueError("artifact identifiers must be non-empty strings")

    entries = tuple(
        ArtifactBatchIntakeEntry(
            artifact_id=artifact_id,
            report=assess_artifact_intake(artifacts[artifact_id]),
        )
        for artifact_id in sorted(artifacts)
    )
    evidence = [entry.to_dict() for entry in entries]
    return ArtifactBatchIntakeReport(
        entries=entries,
        fingerprint=canonical_json_fingerprint(evidence),
    )
