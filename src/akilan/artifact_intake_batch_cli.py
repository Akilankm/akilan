"""Installed fail-closed gate for an exact manifest-defined artifact set."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .artifact_intake_batch import assess_artifact_batch_intake
from .artifact_intake_cli import _load_artifact, _resolve_document_path
from .canonical_json import canonical_json_fingerprint
from .report_io import write_json_report


def build_parser() -> argparse.ArgumentParser:
    """Build the batch artifact intake command parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-artifact-intake-batch",
        description=(
            "Assess an exact manifest-defined artifact set before downstream consumption. "
            "This command never migrates or mutates artifacts."
        ),
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="JSON object mapping non-empty artifact identifiers to artifact directories or document.json files",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for deterministic machine-readable batch intake evidence",
    )
    return parser


def _manifest_failure(path: Path, status: str, message: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "status": status,
        "message": message,
        "manifest_path": str(path),
        "total_count": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "fingerprint": canonical_json_fingerprint([]),
        "entries": [],
    }


def _load_manifest(path: Path) -> tuple[Mapping[str, Any] | None, dict[str, Any] | None]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        return None, _manifest_failure(resolved, "missing", "artifact manifest does not exist")
    if not resolved.is_file():
        return None, _manifest_failure(resolved, "not_a_file", "artifact manifest is not a regular file")
    try:
        raw = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, _manifest_failure(resolved, "unreadable", "artifact manifest could not be read as UTF-8")
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError:
        return None, _manifest_failure(resolved, "invalid_json", "artifact manifest is not valid JSON")
    if not isinstance(manifest, Mapping):
        return None, _manifest_failure(resolved, "invalid_root", "artifact manifest root must be an object")
    return manifest, None


def _resolve_manifest_source(manifest_path: Path, source: str) -> Path:
    candidate = Path(source).expanduser()
    if not candidate.is_absolute():
        candidate = manifest_path.parent / candidate
    return _resolve_document_path(candidate)


def _document_integrity(path: Path) -> dict[str, Any]:
    """Return immutable byte identity for a readable regular document file."""

    if not path.is_file():
        return {"document_sha256": None, "document_size_bytes": None}
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError:
        return {"document_sha256": None, "document_size_bytes": None}
    return {"document_sha256": digest.hexdigest(), "document_size_bytes": size}


def _assess_manifest(manifest_path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    invalid_ids = [artifact_id for artifact_id in manifest if not isinstance(artifact_id, str) or not artifact_id]
    invalid_sources = [artifact_id for artifact_id, source in manifest.items() if not isinstance(source, str) or not source]
    if invalid_ids:
        return _manifest_failure(manifest_path, "invalid_identifier", "artifact identifiers must be non-empty strings")
    if invalid_sources:
        return _manifest_failure(manifest_path, "invalid_source", "artifact sources must be non-empty strings")

    artifacts: dict[str, Mapping[str, Any]] = {}
    source_failures: dict[str, dict[str, Any]] = {}
    source_paths: dict[str, str] = {}
    source_integrity: dict[str, dict[str, Any]] = {}
    for artifact_id in sorted(manifest):
        source_path = _resolve_manifest_source(manifest_path, manifest[artifact_id])
        source_paths[artifact_id] = str(source_path)
        source_integrity[artifact_id] = _document_integrity(source_path)
        artifact, failure = _load_artifact(source_path)
        if failure is not None:
            source_failures[artifact_id] = {
                "artifact_id": artifact_id,
                **failure,
                **source_integrity[artifact_id],
            }
        else:
            assert artifact is not None
            artifacts[artifact_id] = artifact

    assessment = assess_artifact_batch_intake(artifacts)
    assessed_entries = {
        entry.artifact_id: {
            **entry.to_dict(),
            "source_path": source_paths[entry.artifact_id],
            **source_integrity[entry.artifact_id],
        }
        for entry in assessment.entries
    }
    entries = [
        assessed_entries[artifact_id] if artifact_id in assessed_entries else source_failures[artifact_id]
        for artifact_id in sorted(manifest)
    ]
    accepted_count = sum(bool(entry.get("accepted")) for entry in entries)
    accepted = bool(entries) and accepted_count == len(entries)
    return {
        "accepted": accepted,
        "status": "accepted" if accepted else "rejected",
        "manifest_path": str(manifest_path),
        "total_count": len(entries),
        "accepted_count": accepted_count,
        "rejected_count": len(entries) - accepted_count,
        "fingerprint": canonical_json_fingerprint(entries),
        "entries": entries,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the fail-closed batch artifact intake gate."""

    parser = build_parser()
    args = parser.parse_args(argv)
    manifest_path = args.manifest.expanduser().resolve()
    manifest, failure = _load_manifest(manifest_path)
    payload = failure if failure is not None else _assess_manifest(manifest_path, manifest or {})

    report_path: Path | None = None
    if args.report is not None:
        report_path = write_json_report(payload, args.report)
    output = {**payload, "report": str(report_path) if report_path is not None else None}
    stream = sys.stdout if payload["accepted"] else sys.stderr
    print(json.dumps(output, indent=2, sort_keys=True), file=stream)
    return 0 if payload["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())