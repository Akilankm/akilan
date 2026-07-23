"""Deterministic preflight and all-or-nothing acquisition for output leases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

from .output_lease import (
    OutputBuildLease,
    OutputLeaseError,
    OutputLeaseInspection,
    inspect_output_build_lease,
)


class OutputLeaseBatchContextError(OutputLeaseError):
    """Preserve both a protected-block failure and a lease cleanup failure."""

    def __init__(self, body_error: BaseException, release_error: OutputLeaseError):
        self.body_error = body_error
        self.release_error = release_error
        super().__init__(
            "Output lease batch protected operation failed and lease cleanup was "
            f"incomplete: body={type(body_error).__name__}:{body_error}; "
            f"cleanup={type(release_error).__name__}:{release_error}"
        )


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


class OutputBuildLeaseBatch:
    """Acquire an exact destination set or retain none of its leases.

    Destinations are normalized and acquired in deterministic identifier order.
    If acquisition fails, leases acquired by this instance are released in reverse
    order. Existing or malformed foreign lease evidence is never modified.
    """

    def __init__(self, destinations: Mapping[str, str | Path]):
        preflight = assess_output_lease_batch_preflight(destinations)
        if not preflight.ready:
            raise OutputLeaseError(
                "Output lease batch is not acquirable: "
                f"status={preflight.status}; violations={list(preflight.violations)}; "
                f"blocked_count={preflight.blocked_count}"
            )
        self._leases = tuple(
            (
                entry.identifier,
                OutputBuildLease(entry.inspection.destination),
            )
            for entry in preflight.entries
        )
        self._acquired_indices: list[int] = []

    @property
    def acquired(self) -> bool:
        """Return whether this instance currently owns every requested lease."""

        return bool(self._leases) and len(self._acquired_indices) == len(self._leases)

    @property
    def identifiers(self) -> tuple[str, ...]:
        """Return deterministic caller-defined identifiers."""

        return tuple(identifier for identifier, _ in self._leases)

    @property
    def leases(self) -> Mapping[str, OutputBuildLease]:
        """Return a snapshot of acquired lease objects by identifier."""

        return dict(self._leases)

    def acquire(self) -> OutputBuildLeaseBatch:
        """Acquire every lease, rolling back this instance on partial failure."""

        if self._acquired_indices:
            raise OutputLeaseError("Output lease batch has already started acquisition")
        try:
            for index, (_, lease) in enumerate(self._leases):
                lease.acquire()
                self._acquired_indices.append(index)
        except BaseException as acquisition_error:
            rollback_errors = self._release_acquired()
            if rollback_errors:
                detail = "; ".join(rollback_errors)
                raise OutputLeaseError(
                    "Output lease batch acquisition failed and rollback was incomplete: "
                    f"{detail}"
                ) from acquisition_error
            raise
        return self

    def release(self) -> None:
        """Release every independently verified lease in reverse order."""

        rollback_errors = self._release_acquired()
        if rollback_errors:
            detail = "; ".join(rollback_errors)
            raise OutputLeaseError(f"Output lease batch release was incomplete: {detail}")

    def _release_acquired(self) -> list[str]:
        errors: list[str] = []
        retained_indices: list[int] = []
        for index in reversed(self._acquired_indices):
            identifier, lease = self._leases[index]
            try:
                lease.release()
            except BaseException as error:  # preserve only disputed ownership evidence
                errors.append(f"{identifier}:{type(error).__name__}:{error}")
                retained_indices.append(index)
        self._acquired_indices = list(reversed(retained_indices))
        return errors

    def __enter__(self) -> OutputBuildLeaseBatch:
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self.release()
        except OutputLeaseError as release_error:
            if exc_value is None:
                raise
            raise OutputLeaseBatchContextError(exc_value, release_error) from exc_value


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
