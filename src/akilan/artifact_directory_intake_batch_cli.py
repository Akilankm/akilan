"""Installed fail-closed gate for an exact manifest-defined artifact directory set."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .artifact_directory_intake_batch import assess_artifact_directory_batch_intake
from .canonical_json import canonical_json_fingerprint
from .report_io import write_json_report


def build_parser() -> argparse.ArgumentParser:
    """Build the batch artifact directory intake command parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-artifact-directory-intake-batch",
        description=(
            "Assess an exact manifest-defined set of persisted artifact directories. "
            "This command never repairs, migrates, or mutates artifacts."
        ),
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="JSON object mapping non-empty identifiers to artifact directory paths",
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
        return None, _manifest_failure(resolved, "missing", "artifact directory manifest does not exist")
    if not resolved.is_file():
        return None, _manifest_failure(
            resolved,
            "not_a_file",
            "artifact directory manifest is not a regular file",
        )
    try:
        raw = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, _manifest_failure(
            resolved,
            "unreadable",
            "artifact directory manifest could not be read as UTF-8",
        )
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError:
        return None, _manifest_failure(
            resolved,
            "invalid_json",
            "artifact directory manifest is not valid JSON",
        )
    if not isinstance(manifest, Mapping):
        return None, _manifest_failure(
            resolved,
            "invalid_root",
            "artifact directory manifest root must be an object",
        )
    return manifest, None


def _resolve_roots(manifest_path: Path, manifest: Mapping[str, Any]) -> tuple[dict[str, Path] | None, dict[str, Any] | None]:
    invalid_ids = [identifier for identifier in manifest if not isinstance(identifier, str) or not identifier]
    if invalid_ids:
        return None, _manifest_failure(
            manifest_path,
            "invalid_identifier",
            "artifact directory identifiers must be non-empty strings",
        )

    invalid_sources = [
        identifier
        for identifier, source in manifest.items()
        if not isinstance(source, str) or not source
    ]
    if invalid_sources:
        return None, _manifest_failure(
            manifest_path,
            "invalid_source",
            "artifact directory sources must be non-empty strings",
        )

    roots: dict[str, Path] = {}
    for identifier in sorted(manifest):
        candidate = Path(manifest[identifier]).expanduser()
        if not candidate.is_absolute():
            candidate = manifest_path.parent / candidate
        roots[identifier] = candidate.resolve(strict=False)
    return roots, None


def _assess_manifest(manifest_path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    roots, failure = _resolve_roots(manifest_path, manifest)
    if failure is not None:
        return failure
    assessment = assess_artifact_directory_batch_intake(roots or {})
    return {
        **assessment.to_dict(),
        "manifest_path": str(manifest_path),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the fail-closed batch artifact directory intake gate."""

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
