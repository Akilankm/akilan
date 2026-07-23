"""Read-only security diagnostics for artifact output lease permissions."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .output_lease import inspect_output_build_lease


@dataclass(frozen=True, slots=True)
class OutputLeasePermissionInspection:
    """POSIX permission evidence for one artifact output lease."""

    destination: str
    lease_path: str
    status: str
    lease_mode: str | None
    owner_mode: str | None
    violations: tuple[str, ...]

    @property
    def secure(self) -> bool:
        """Return whether the permission boundary is acceptable."""

        return not self.violations and self.status in {"absent", "secure", "unsupported"}

    def to_dict(self) -> dict[str, object]:
        """Serialize deterministic machine-readable evidence."""

        return {
            "destination": self.destination,
            "lease_path": self.lease_path,
            "status": self.status,
            "secure": self.secure,
            "lease_mode": self.lease_mode,
            "owner_mode": self.owner_mode,
            "violations": list(self.violations),
        }


def inspect_output_build_lease_permissions(
    destination: str | Path,
) -> OutputLeasePermissionInspection:
    """Inspect lease permissions without mutating or recovering the lease.

    On POSIX systems, group/world write access is rejected for both the lease
    directory and ``owner.json``. On non-POSIX platforms, the structural lease
    inspection remains authoritative and permission auditing reports
    ``unsupported`` rather than guessing at ACL semantics.
    """

    structural = inspect_output_build_lease(destination)
    if structural.status == "absent":
        return OutputLeasePermissionInspection(
            destination=structural.destination,
            lease_path=structural.lease_path,
            status="absent",
            lease_mode=None,
            owner_mode=None,
            violations=(),
        )
    if not structural.valid:
        return OutputLeasePermissionInspection(
            destination=structural.destination,
            lease_path=structural.lease_path,
            status="invalid_lease_evidence",
            lease_mode=None,
            owner_mode=None,
            violations=("structural_lease_validation_failed",),
        )
    if os.name != "posix":
        return OutputLeasePermissionInspection(
            destination=structural.destination,
            lease_path=structural.lease_path,
            status="unsupported",
            lease_mode=None,
            owner_mode=None,
            violations=(),
        )

    lease_path = Path(structural.lease_path)
    owner_path = lease_path / "owner.json"
    try:
        lease_stat = lease_path.stat(follow_symlinks=False)
        owner_stat = owner_path.stat(follow_symlinks=False)
    except OSError:
        return OutputLeasePermissionInspection(
            destination=structural.destination,
            lease_path=structural.lease_path,
            status="unreadable_permissions",
            lease_mode=None,
            owner_mode=None,
            violations=("permission_metadata_must_be_readable",),
        )

    lease_mode_value = stat.S_IMODE(lease_stat.st_mode)
    owner_mode_value = stat.S_IMODE(owner_stat.st_mode)
    violations: list[str] = []
    if lease_mode_value & (stat.S_IWGRP | stat.S_IWOTH):
        violations.append("lease_directory_must_not_be_group_or_world_writable")
    if owner_mode_value & (stat.S_IWGRP | stat.S_IWOTH):
        violations.append("owner_json_must_not_be_group_or_world_writable")

    return OutputLeasePermissionInspection(
        destination=structural.destination,
        lease_path=structural.lease_path,
        status="secure" if not violations else "insecure_permissions",
        lease_mode=f"{lease_mode_value:04o}",
        owner_mode=f"{owner_mode_value:04o}",
        violations=tuple(violations),
    )
