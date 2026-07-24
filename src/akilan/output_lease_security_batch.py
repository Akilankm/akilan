"""Deterministic read-only permission audit for exact output lease sets."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .output_lease_security import (
    OutputLeasePermissionInspection,
    inspect_output_build_lease_permissions,
)


@dataclass(frozen=True, slots=True)
class OutputLeasePermissionBatchEntry:
    """Permission evidence bound to one caller-defined destination identifier."""

    identifier: str
    inspection: OutputLeasePermissionInspection

    def to_dict(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "inspection": self.inspection.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class OutputLeasePermissionBatchInspection:
    """Fail-closed permission evidence for an exact destination set."""

    status: str
    entries: tuple[OutputLeasePermissionBatchEntry, ...]
    violations: tuple[str, ...]

    @property
    def secure(self) -> bool:
        """Return whether every destination has acceptable permission evidence."""

        return self.status == "secure"

    @property
    def destination_count(self) -> int:
        return len(self.entries)

    @property
    def insecure_count(self) -> int:
        return sum(not entry.inspection.secure for entry in self.entries)

    def to_dict(self) -> dict[str, object]:
        """Serialize deterministic machine-readable evidence."""

        return {
            "status": self.status,
            "secure": self.secure,
            "destination_count": self.destination_count,
            "insecure_count": self.insecure_count,
            "entries": [entry.to_dict() for entry in self.entries],
            "violations": list(self.violations),
        }


def inspect_output_lease_permission_batch(
    destinations: Mapping[str, str | Path],
) -> OutputLeasePermissionBatchInspection:
    """Audit an exact output set without mutating any lease or permissions.

    Identifiers and resolved destinations must be unique. Entries are emitted in
    deterministic identifier order. Any structurally invalid, insecure, unreadable,
    or unsupported permission result fails the complete set closed.
    """

    if not destinations:
        return OutputLeasePermissionBatchInspection(
            status="invalid_destination_set",
            entries=(),
            violations=("destination_set_must_not_be_empty",),
        )

    if any(
        not isinstance(identifier, str) or not identifier.strip()
        for identifier in destinations
    ):
        return OutputLeasePermissionBatchInspection(
            status="invalid_destination_set",
            entries=(),
            violations=("destination_identifiers_must_be_non_empty_strings",),
        )

    entries = tuple(
        OutputLeasePermissionBatchEntry(
            identifier=identifier,
            inspection=inspect_output_build_lease_permissions(destinations[identifier]),
        )
        for identifier in sorted(destinations)
    )

    resolved_destinations: dict[str, str] = {}
    duplicate_violations: list[str] = []
    for entry in entries:
        destination = entry.inspection.destination
        existing = resolved_destinations.get(destination)
        if existing is not None:
            duplicate_violations.append(
                f"duplicate_destination:{existing}:{entry.identifier}"
            )
        else:
            resolved_destinations[destination] = entry.identifier

    if duplicate_violations:
        return OutputLeasePermissionBatchInspection(
            status="invalid_destination_set",
            entries=entries,
            violations=tuple(duplicate_violations),
        )

    insecure_entries = [
        entry.identifier for entry in entries if not entry.inspection.secure
    ]
    if insecure_entries:
        return OutputLeasePermissionBatchInspection(
            status="insecure",
            entries=entries,
            violations=tuple(
                f"destination_permission_audit_failed:{identifier}"
                for identifier in insecure_entries
            ),
        )

    return OutputLeasePermissionBatchInspection(
        status="secure",
        entries=entries,
        violations=(),
    )
