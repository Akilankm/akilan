"""Combined compatibility and structural validation for artifact intake."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .schema import SchemaViolation, validate_artifact
from .schema_compatibility import SchemaCompatibilityReport, assess_schema_compatibility


@dataclass(frozen=True, slots=True)
class ArtifactIntakeReport:
    """Deterministic evidence for one artifact-consumption decision."""

    compatibility: SchemaCompatibilityReport
    violations: tuple[SchemaViolation, ...]

    @property
    def accepted(self) -> bool:
        """Return whether the artifact is compatible and structurally valid."""

        return self.compatibility.compatible and not self.violations

    def to_dict(self) -> dict[str, Any]:
        """Serialize stable, machine-readable intake evidence."""

        return {
            "accepted": self.accepted,
            "compatibility": self.compatibility.to_dict(),
            "violation_count": len(self.violations),
            "violations": [
                {"path": violation.path, "message": violation.message}
                for violation in self.violations
            ],
        }


def assess_artifact_intake(artifact: Mapping[str, Any]) -> ArtifactIntakeReport:
    """Fail closed on incompatible schema versions or structural violations.

    Compatibility is evaluated first. Structural validation still runs so callers
    receive actionable repair evidence, but acceptance is impossible unless both
    boundaries pass. The artifact is never mutated or migrated.
    """

    compatibility = assess_schema_compatibility(artifact.get("schema_version"))
    violations = tuple(validate_artifact(artifact, raise_on_error=False))
    return ArtifactIntakeReport(
        compatibility=compatibility,
        violations=violations,
    )
