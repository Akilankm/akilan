"""Deterministic read-only preflight for multiple artifact output leases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .output_lease import OutputLeaseInspection, inspect_output_build_lease


@dataclass(frozen=True, slots=True)
class OutputLeaseBatchEntry:
    """Lease inspection evidence bound to one caller-defined identifier."""

    identifier: str
    inspection: OutputLeaseInspection

    def to_dict(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "inspection": self.inspection.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class OutputLeaseBatchPreflight:
    """Fail-closed readiness evidence for an exact destination set."""

    status: str
    entries: tuple[OutputLeaseBatchEntry, ...]
    violations: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.status == "ready"

    @property
    def destination_count(self) -> int:
        return len(self.entries)

    @property
    def blocked_count(self) -> int:
        return sum(entry.inspection.status != "absent" for entry in self.entries)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "ready": self.ready,
            "destination_count": self.destination_count,
            "blocked_count": self.blocked_count,
            "entries": [entry.to_dict() for entry in self.entries],
            "violations": list(self.violations),
        }


def assess_output_lease_batch_preflight(
    destinations: Mapping[str, str | Path],
) -> OutputLeaseBatchPreflight:
    """Inspect an exact output set and allow scheduling only when every lease is absent.

    The operation is read-only. It never acquires, releases, repairs, removes, or
    declares a lease stale. Entries are emitted in deterministic identifier order.
    """

    if not destinations:
        return OutputLeaseBatchPreflight(
            status="invalid_destination_set",
            entries=(),
            violations=("destination_set_must_not_be_empty",),
        )

    identifier_violations = [
        "destination_identifiers_must_be_non_empty_strings"
        for identifier in destinations
        if not isinstance(identifier, str) or not identifier.strip()
    ]
    if identifier_violations:
        return OutputLeaseBatchPreflight(
            status="invalid_destination_set",
            entries=(),
            violations=tuple(dict.fromkeys(identifier_violations)),
        )

    entries = tuple(
        OutputLeaseBatchEntry(
            identifier=identifier,
            inspection=inspect_output_build_lease(destinations[identifier]),
        )
        for identifier in sorted(destinations)
    )

    resolved_destinations: dict[str, str] = {}
    duplicate_destinations: list[str] = []
    for entry in entries:
        existing_identifier = resolved_destinations.get(entry.inspection.destination)
        if existing_identifier is not None:
            duplicate_destinations.append(
                f"duplicate_destination:{existing_identifier}:{entry.identifier}"
            )
        else:
            resolved_destinations[entry.inspection.destination] = entry.identifier

    if duplicate_destinations:
        return OutputLeaseBatchPreflight(
            status="invalid_destination_set",
            entries=entries,
            violations=tuple(duplicate_destinations),
        )

    if any(entry.inspection.status != "absent" for entry in entries):
        return OutputLeaseBatchPreflight(
            status="blocked",
            entries=entries,
            violations=(),
        )

    return OutputLeaseBatchPreflight(status="ready", entries=entries, violations=())
