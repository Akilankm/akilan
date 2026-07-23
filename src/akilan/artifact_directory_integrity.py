"""Deterministic read-only integrity evidence for complete artifact directories."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical_json import canonical_json_fingerprint


@dataclass(frozen=True, slots=True)
class ArtifactDirectoryFile:
    """Byte identity for one regular file in an artifact directory."""

    relative_path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize stable file evidence."""

        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class ArtifactDirectoryIntegrityReport:
    """Fail-closed integrity evidence for one complete artifact directory."""

    root_path: str
    status: str
    message: str
    files: tuple[ArtifactDirectoryFile, ...]
    fingerprint: str

    @property
    def accepted(self) -> bool:
        """Return whether a complete regular-file inventory was produced."""

        return self.status == "accepted"

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def total_size_bytes(self) -> int:
        return sum(file.size_bytes for file in self.files)

    def to_dict(self) -> dict[str, Any]:
        """Serialize deterministic machine-readable integrity evidence."""

        return {
            "accepted": self.accepted,
            "status": self.status,
            "message": self.message,
            "root_path": self.root_path,
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
            "fingerprint": self.fingerprint,
            "files": [file.to_dict() for file in self.files],
        }


def _rejected(root: Path, status: str, message: str) -> ArtifactDirectoryIntegrityReport:
    return ArtifactDirectoryIntegrityReport(
        root_path=str(root),
        status=status,
        message=message,
        files=(),
        fingerprint=canonical_json_fingerprint([]),
    )


def _same_file_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    """Return whether two stat results describe the same unchanged regular file."""

    return (
        stat.S_ISREG(left.st_mode)
        and stat.S_ISREG(right.st_mode)
        and left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
    )


def _read_stable_regular_file(path: Path) -> bytes:
    """Read one regular file while detecting symlink swaps and concurrent mutation."""

    before_path = path.lstat()
    if not stat.S_ISREG(before_path.st_mode):
        raise ValueError("not_regular")

    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor = os.open(path, flags)
    try:
        before_fd = os.fstat(descriptor)
        if not _same_file_snapshot(before_path, before_fd):
            raise RuntimeError("changed_during_read")

        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)

        after_fd = os.fstat(descriptor)
        after_path = path.lstat()
        if not _same_file_snapshot(before_fd, after_fd) or not _same_file_snapshot(
            before_fd,
            after_path,
        ):
            raise RuntimeError("changed_during_read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def assess_artifact_directory_integrity(
    artifact_root: str | Path,
) -> ArtifactDirectoryIntegrityReport:
    """Hash every regular file under an artifact directory without following symlinks.

    The canonical ``document.json`` file is required. Paths are normalized to relative
    POSIX form and emitted lexicographically. Any symlink, unreadable file, missing
    canonical document, source-type mismatch, or concurrent mutation rejects the
    complete directory.
    """

    candidate = Path(artifact_root).expanduser()
    if candidate.is_symlink():
        return _rejected(
            candidate.absolute(),
            "symlink_rejected",
            "artifact root must not be a symlink",
        )
    root = candidate.resolve()
    if not root.exists():
        return _rejected(root, "missing", "artifact directory does not exist")
    if not root.is_dir():
        return _rejected(root, "not_a_directory", "artifact root is not a directory")

    document = root / "document.json"
    if not document.exists():
        return _rejected(
            root,
            "missing_document",
            "artifact directory does not contain document.json",
        )
    if document.is_symlink():
        return _rejected(root, "symlink_rejected", "artifact directory contains a symlink")
    if not document.is_file():
        return _rejected(
            root,
            "invalid_document",
            "artifact document.json is not a regular file",
        )

    entries: list[ArtifactDirectoryFile] = []
    paths = sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix())
    for path in paths:
        if path.is_symlink():
            return _rejected(root, "symlink_rejected", "artifact directory contains a symlink")
        if path.is_dir():
            continue
        if not path.is_file():
            return _rejected(
                root,
                "unsupported_entry",
                "artifact directory contains a non-regular entry",
            )
        try:
            raw = _read_stable_regular_file(path)
        except ValueError:
            return _rejected(
                root,
                "unsupported_entry",
                "artifact directory contains a non-regular entry",
            )
        except RuntimeError:
            return _rejected(
                root,
                "changed_during_read",
                "artifact directory changed while integrity evidence was generated",
            )
        except OSError:
            return _rejected(
                root,
                "unreadable",
                "artifact directory contains an unreadable file",
            )
        entries.append(
            ArtifactDirectoryFile(
                relative_path=path.relative_to(root).as_posix(),
                sha256=hashlib.sha256(raw).hexdigest(),
                size_bytes=len(raw),
            )
        )

    evidence = [entry.to_dict() for entry in entries]
    return ArtifactDirectoryIntegrityReport(
        root_path=str(root),
        status="accepted",
        message="artifact directory integrity evidence generated",
        files=tuple(entries),
        fingerprint=canonical_json_fingerprint(evidence),
    )
