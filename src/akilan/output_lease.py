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


class OutputBuildLease:
    """Exclusive, fail-fast lease protecting one artifact destination.

    Directory creation is the atomic arbitration operation. The lease is held
    from pre-build destination validation through final publication. Automatic
    stale-lock removal is intentionally prohibited because process identity
    cannot be established safely across hosts and container namespaces.
    """

    def __init__(self, destination: str | Path):
        self.destination = Path(destination).expanduser().resolve()
        self.path = self.destination.parent / f".{self.destination.name}.akilan.lock"
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
            owner = _read_owner(self.path)
            detail = f" Existing owner evidence: {owner}." if owner is not None else ""
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


def _write_owner(lock_path: Path, owner: OutputLeaseOwner) -> None:
    payload = json.dumps(owner.to_dict(), indent=2, sort_keys=True) + "\n"
    (lock_path / "owner.json").write_text(payload, encoding="utf-8")


def _read_owner(lock_path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads((lock_path / "owner.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None
