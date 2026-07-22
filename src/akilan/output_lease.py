"""Fail-closed same-destination coordination for artifact publication."""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from uuid import uuid4


class OutputLeaseError(RuntimeError):
    """Raised when an artifact destination is already leased by another build."""


@dataclass(frozen=True, slots=True)
class OutputLeaseOwner:
    """Diagnostic identity persisted inside an acquired output lease."""

    token: str
    process_id: int
    hostname: str
    acquired_at_utc: str
    destination: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "token": self.token,
            "process_id": self.process_id,
            "hostname": self.hostname,
            "acquired_at_utc": self.acquired_at_utc,
            "destination": self.destination,
        }


@dataclass(frozen=True, slots=True)
class OutputLeaseInspection:
    """Read-only diagnostic evidence for one artifact destination lease."""

    destination: str
    lease_path: str
    status: str
    present: bool
    owner: dict[str, object] | None
    violations: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.status in {"absent", "valid"}

    def to_dict(self) -> dict[str, object]:
        return {
            "destination": self.destination,
            "lease_path": self.lease_path,
            "status": self.status,
            "present": self.present,
            "valid": self.valid,
            "owner": self.owner,
            "violations": list(self.violations),
        }


class OutputBuildLease:
    """Exclusive, fail-fast lease protecting one artifact destination.

    Directory creation is the atomic arbitration operation. The lease is held
    from pre-build destination validation through final publication. Automatic
    stale-lock removal is intentionally prohibited because process identity
    cannot be established safely across hosts and container namespaces.
    """

    def __init__(self, destination: str | Path):
        self.destination = Path(destination).expanduser().resolve()
        self.path = _lease_path(self.destination)
        self.owner = OutputLeaseOwner(
            token=uuid4().hex,
            process_id=os.getpid(),
            hostname=socket.gethostname(),
            acquired_at_utc=datetime.now(timezone.utc).isoformat(),
            destination=str(self.destination),
        )
        self._acquired = False

    def acquire(self) -> OutputBuildLease:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.path.mkdir()
        except FileExistsError as error:
            inspection = inspect_output_build_lease(self.destination)
            detail = f" Existing owner evidence: {inspection.owner}." if inspection.owner else ""
            raise OutputLeaseError(
                f"Artifact output is already leased: {self.destination}.{detail} "
                f"Do not remove an active lease. Recover abandoned leases only after independently "
                f"confirming that no writer is using the destination."
            ) from error

        try:
            _write_owner(self.path, self.owner)
        except Exception:
            self.path.rmdir()
            raise
        self._acquired = True
        return self

    def release(self) -> None:
        if not self._acquired:
            return
        owner = _read_owner(self.path)
        if owner is None or owner.get("token") != self.owner.token:
            raise OutputLeaseError(
                f"Refusing to release artifact output lease because ownership changed: {self.path}"
            )
        (self.path / "owner.json").unlink()
        self.path.rmdir()
        self._acquired = False

    def __enter__(self) -> OutputBuildLease:
        return self.acquire()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()


def inspect_output_build_lease(destination: str | Path) -> OutputLeaseInspection:
    """Inspect lease evidence without mutating or recovering the lease."""

    resolved_destination = Path(destination).expanduser().resolve()
    lock_path = _lease_path(resolved_destination)
    if not lock_path.exists():
        return OutputLeaseInspection(
            destination=str(resolved_destination),
            lease_path=str(lock_path),
            status="absent",
            present=False,
            owner=None,
            violations=(),
        )
    if not lock_path.is_dir() or lock_path.is_symlink():
        return OutputLeaseInspection(
            destination=str(resolved_destination),
            lease_path=str(lock_path),
            status="invalid_lease_path",
            present=True,
            owner=None,
            violations=("lease_path_must_be_a_regular_directory",),
        )

    owner = _read_owner(lock_path)
    if owner is None:
        return OutputLeaseInspection(
            destination=str(resolved_destination),
            lease_path=str(lock_path),
            status="invalid_owner_evidence",
            present=True,
            owner=None,
            violations=("owner_json_must_be_a_utf8_json_object",),
        )

    violations = _owner_violations(owner, resolved_destination)
    return OutputLeaseInspection(
        destination=str(resolved_destination),
        lease_path=str(lock_path),
        status="valid" if not violations else "invalid_owner_evidence",
        present=True,
        owner=owner,
        violations=tuple(violations),
    )


def _lease_path(destination: Path) -> Path:
    return destination.parent / f".{destination.name}.akilan.lock"


def _owner_violations(owner: dict[str, object], destination: Path) -> list[str]:
    violations: list[str] = []
    token = owner.get("token")
    if not isinstance(token, str) or len(token) != 32 or any(char not in "0123456789abcdef" for char in token):
        violations.append("token_must_be_lowercase_uuid4_hex")
    process_id = owner.get("process_id")
    if not isinstance(process_id, int) or isinstance(process_id, bool) or process_id <= 0:
        violations.append("process_id_must_be_positive_integer")
    hostname = owner.get("hostname")
    if not isinstance(hostname, str) or not hostname.strip():
        violations.append("hostname_must_be_non_empty_string")
    acquired_at = owner.get("acquired_at_utc")
    if not isinstance(acquired_at, str) or not _is_utc_datetime(acquired_at):
        violations.append("acquired_at_utc_must_be_valid_utc_datetime")
    recorded_destination = owner.get("destination")
    if recorded_destination != str(destination):
        violations.append("destination_must_match_requested_destination")
    return violations


def _is_utc_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _write_owner(lock_path: Path, owner: OutputLeaseOwner) -> None:
    payload = json.dumps(owner.to_dict(), indent=2, sort_keys=True) + "\n"
    (lock_path / "owner.json").write_text(payload, encoding="utf-8")


def _read_owner(lock_path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads((lock_path / "owner.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None
