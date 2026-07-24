"""Fail-closed same-destination coordination for artifact publication."""

from __future__ import annotations

import json
import os
import socket
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from uuid import RFC_4122, UUID, uuid4

_MAX_OWNER_EVIDENCE_BYTES = 16 * 1024
_OWNER_KEYS = frozenset(
    {
        "token",
        "process_id",
        "hostname",
        "acquired_at_utc",
        "destination",
    }
)


class OutputLeaseError(RuntimeError):
    """Raised when an artifact destination is already leased by another build."""


class OutputLeaseContextError(OutputLeaseError):
    """Preserve both a protected-operation failure and a lease cleanup failure."""

    def __init__(self, body_error: BaseException, release_error: OutputLeaseError):
        self.body_error = body_error
        self.release_error = release_error
        super().__init__(
            "Output lease protected operation failed and lease cleanup was incomplete: "
            f"body={type(body_error).__name__}:{body_error}; "
            f"cleanup={type(release_error).__name__}:{release_error}"
        )


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
            _set_posix_mode(self.path, 0o700)
            _write_owner(self.path, self.owner)
        except BaseException as acquisition_error:
            try:
                _rollback_owner_publication(self.path, self.owner)
            except Exception:
                raise OutputLeaseError(
                    "Artifact output lease owner publication failed and rollback "
                    f"could not prove safe cleanup: {self.path}"
                ) from acquisition_error
            raise
        self._acquired = True
        return self

    def release(self) -> None:
        if not self._acquired:
            return
        inspection = inspect_output_build_lease(self.destination)
        if inspection.status != "valid" or inspection.owner != self.owner.to_dict():
            raise OutputLeaseError(
                f"Refusing to release artifact output lease because ownership changed: {self.path}"
            )
        (self.path / "owner.json").unlink()
        self.path.rmdir()
        self._acquired = False
        try:
            _sync_directory(self.path.parent)
        except OSError as error:
            raise OutputLeaseError(
                "Artifact output lease was removed but its parent directory could not be "
                f"synchronized: {self.path.parent}"
            ) from error

    def __enter__(self) -> OutputBuildLease:
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
            raise OutputLeaseContextError(exc_value, release_error) from exc_value


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

    entry_violations = _lease_entry_violations(lock_path)
    owner = _read_owner(lock_path)
    if owner is None:
        return OutputLeaseInspection(
            destination=str(resolved_destination),
            lease_path=str(lock_path),
            status="invalid_owner_evidence",
            present=True,
            owner=None,
            violations=tuple(entry_violations or ["owner_json_must_be_a_utf8_json_object"]),
        )

    violations = [*entry_violations, *_owner_violations(owner, resolved_destination)]
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


def _lease_entry_violations(lock_path: Path) -> list[str]:
    try:
        entries = list(lock_path.iterdir())
    except OSError:
        return ["lease_directory_must_be_readable"]
    if len(entries) != 1 or entries[0].name != "owner.json":
        return ["lease_directory_must_contain_only_owner_json"]
    owner_path = entries[0]
    try:
        owner_stat = owner_path.stat(follow_symlinks=False)
    except OSError:
        return ["owner_json_must_be_a_regular_file"]
    if not stat.S_ISREG(owner_stat.st_mode):
        return ["owner_json_must_be_a_regular_file"]
    if owner_stat.st_nlink != 1:
        return ["owner_json_must_have_single_link"]
    return []


def _owner_violations(owner: dict[str, object], destination: Path) -> list[str]:
    violations: list[str] = []
    if set(owner) != _OWNER_KEYS:
        violations.append("owner_json_must_have_exact_fields")
    token = owner.get("token")
    if not isinstance(token, str) or not _is_uuid4_token(token):
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


def _is_uuid4_token(value: str) -> bool:
    if len(value) != 32 or any(char not in "0123456789abcdef" for char in value):
        return False
    try:
        parsed = UUID(hex=value)
    except ValueError:
        return False
    return parsed.hex == value and parsed.version == 4 and parsed.variant == RFC_4122


def _is_utc_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _owner_staging_path(lock_path: Path, owner: OutputLeaseOwner) -> Path:
    return lock_path / f".owner-{owner.token}.tmp"


def _set_posix_mode(path: Path, mode: int) -> None:
    """Apply an exact restrictive mode where POSIX mode bits are meaningful."""

    if os.name == "posix":
        path.chmod(mode)


def _write_owner(lock_path: Path, owner: OutputLeaseOwner) -> None:
    payload = json.dumps(owner.to_dict(), indent=2, sort_keys=True) + "\n"
    staging_path = _owner_staging_path(lock_path, owner)
    staging_path.touch(mode=0o600, exist_ok=False)
    _set_posix_mode(staging_path, 0o600)
    with staging_path.open("w", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staging_path, lock_path / "owner.json")
    _sync_directory(lock_path)


def _sync_directory(path: Path) -> None:
    """Synchronize a directory entry on POSIX filesystems when supported."""

    if os.name != "posix":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rollback_owner_publication(lock_path: Path, owner: OutputLeaseOwner) -> None:
    staging_path = _owner_staging_path(lock_path, owner)
    if staging_path.exists():
        if staging_path.is_symlink() or not staging_path.is_file():
            raise OutputLeaseError("Owner staging evidence changed during acquisition")
        staging_path.unlink()

    owner_path = lock_path / "owner.json"
    if owner_path.exists():
        if owner_path.is_symlink() or not owner_path.is_file():
            raise OutputLeaseError("Owner evidence changed during acquisition")
        persisted_owner = _read_owner(lock_path)
        if persisted_owner != owner.to_dict():
            raise OutputLeaseError("Owner evidence changed during acquisition")
        owner_path.unlink()

    lock_path.rmdir()
    _sync_directory(lock_path.parent)


def _read_owner(lock_path: Path) -> dict[str, object] | None:
    owner_path = lock_path / "owner.json"
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY
        flags |= getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NONBLOCK", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(owner_path, flags)
        owner_stat = os.fstat(descriptor)
        if not stat.S_ISREG(owner_stat.st_mode) or owner_stat.st_nlink != 1:
            return None
        raw_payload = _read_bounded_descriptor(descriptor, _MAX_OWNER_EVIDENCE_BYTES)
        if raw_payload is None:
            return None
        payload = json.loads(raw_payload.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return payload if isinstance(payload, dict) else None


def _read_bounded_descriptor(descriptor: int, limit: int) -> bytes | None:
    """Read at most ``limit`` bytes plus one overflow sentinel from a descriptor."""

    chunks: list[bytes] = []
    remaining = limit + 1
    while remaining:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    payload = b"".join(chunks)
    return payload if len(payload) <= limit else None
