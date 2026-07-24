"""Read-only security diagnostics for artifact output lease permissions."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .output_lease import inspect_output_build_lease

_OPEN = os.open


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
        """Return whether the permission boundary was verified as acceptable."""

        return not self.violations and self.status in {"absent", "secure"}

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

    On supported POSIX systems, group/world write access is rejected for both
    the lease directory and ``owner.json``. Descriptor-relative lookup anchors
    owner metadata to the opened lease directory so a concurrent path
    replacement cannot redirect the audit to unrelated evidence. On platforms
    without these descriptor semantics, auditing reports ``unsupported`` rather
    than guessing at ACL or path-race behavior.
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
    if not _supports_posix_permission_audit():
        return OutputLeasePermissionInspection(
            destination=structural.destination,
            lease_path=structural.lease_path,
            status="unsupported",
            lease_mode=None,
            owner_mode=None,
            violations=("posix_permission_audit_is_unsupported",),
        )

    lease_path = Path(structural.lease_path)
    try:
        lease_stat, owner_stat = _read_permission_metadata(lease_path)
    except OSError:
        return OutputLeasePermissionInspection(
            destination=structural.destination,
            lease_path=structural.lease_path,
            status="unreadable_permissions",
            lease_mode=None,
            owner_mode=None,
            violations=("permission_metadata_must_be_readable",),
        )

    if not stat.S_ISDIR(lease_stat.st_mode) or not stat.S_ISREG(owner_stat.st_mode):
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


def _read_permission_metadata(lock_path: Path) -> tuple[os.stat_result, os.stat_result]:
    """Read lease and owner metadata from one anchored directory descriptor."""

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    owner_flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
    directory_descriptor = _OPEN(lock_path, directory_flags)
    owner_descriptor: int | None = None
    try:
        owner_descriptor = _OPEN("owner.json", owner_flags, dir_fd=directory_descriptor)
        return os.fstat(directory_descriptor), os.fstat(owner_descriptor)
    finally:
        if owner_descriptor is not None:
            os.close(owner_descriptor)
        os.close(directory_descriptor)


def _supports_posix_permission_audit() -> bool:
    """Return whether anchored POSIX mode-bit inspection is supported."""

    return (
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and os.open in os.supports_dir_fd
    )
