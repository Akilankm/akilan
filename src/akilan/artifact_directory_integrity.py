"""Deterministic read-only integrity evidence for complete artifact directories."""

from __future__ import annotations

import hashlib
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


def assess_artifact_directory_integrity(
    artifact_root: str | Path,
) -> ArtifactDirectoryIntegrityReport:
    """Hash every regular file under an artifact directory without following symlinks.

    The canonical ``document.json`` file is required. Paths are normalized to relative
    POSIX form and emitted lexicographically. Any symlink, unreadable file, missing
    canonical document, or source-type mismatch rejects the complete directory.
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
            raw = path.read_bytes()
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
