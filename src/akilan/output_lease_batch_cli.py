"""Installed fail-closed preflight for an exact manifest-defined output set."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .output_lease_batch import assess_output_lease_batch_preflight
from .report_io import write_json_report


def build_parser() -> argparse.ArgumentParser:
    """Build the batch output lease preflight command parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-output-lease-batch",
        description=(
            "Inspect an exact manifest-defined set of artifact output leases. "
            "This command is read-only and never acquires, releases, repairs, or removes leases."
        ),
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="JSON object mapping non-empty identifiers to artifact output destinations",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for deterministic machine-readable preflight evidence",
    )
    return parser


def _failure(path: Path, status: str, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "ready": False,
        "manifest_path": str(path),
        "destination_count": 0,
        "blocked_count": 0,
        "entries": [],
        "violations": [message],
    }


def _load_manifest(path: Path) -> tuple[Mapping[str, Any] | None, dict[str, Any] | None]:
    if not path.exists():
        return None, _failure(path, "missing_manifest", "manifest_does_not_exist")
    if not path.is_file():
        return None, _failure(path, "invalid_manifest_path", "manifest_must_be_a_regular_file")
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, _failure(path, "unreadable_manifest", "manifest_must_be_readable_utf8")
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError:
        return None, _failure(path, "invalid_manifest_json", "manifest_must_contain_valid_json")
    if not isinstance(manifest, Mapping):
        return None, _failure(path, "invalid_manifest_root", "manifest_root_must_be_an_object")
    return manifest, None


def _resolve_destinations(
    manifest_path: Path,
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Path] | None, dict[str, Any] | None]:
    invalid_identifiers = [
        identifier
        for identifier in manifest
        if not isinstance(identifier, str) or not identifier.strip()
    ]
    if invalid_identifiers:
        return None, _failure(
            manifest_path,
            "invalid_destination_identifier",
            "destination_identifiers_must_be_non_empty_strings",
        )

    invalid_destinations = [
        identifier
        for identifier, destination in manifest.items()
        if not isinstance(destination, str) or not destination.strip()
    ]
    if invalid_destinations:
        return None, _failure(
            manifest_path,
            "invalid_destination",
            "destinations_must_be_non_empty_strings",
        )

    destinations: dict[str, Path] = {}
    for identifier in sorted(manifest):
        candidate = Path(manifest[identifier]).expanduser()
        if not candidate.is_absolute():
            candidate = manifest_path.parent / candidate
        destinations[identifier] = candidate.resolve(strict=False)
    return destinations, None


def _assess_manifest(manifest_path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    destinations, failure = _resolve_destinations(manifest_path, manifest)
    if failure is not None:
        return failure
    assessment = assess_output_lease_batch_preflight(destinations or {})
    return {**assessment.to_dict(), "manifest_path": str(manifest_path)}


def main(argv: Sequence[str] | None = None) -> int:
    """Run the manifest-defined batch output lease preflight."""

    parser = build_parser()
    args = parser.parse_args(argv)
    manifest_path = args.manifest.expanduser().resolve()
    manifest, failure = _load_manifest(manifest_path)
    payload = failure if failure is not None else _assess_manifest(manifest_path, manifest or {})

    report_path: Path | None = None
    if args.report is not None:
        try:
            report_path = write_json_report(payload, args.report)
        except OSError as exc:
            parser.error(f"unable to write report: {exc.__class__.__name__}")

    output = {**payload, "report": str(report_path) if report_path is not None else None}
    stream = sys.stdout if payload["ready"] else sys.stderr
    print(json.dumps(output, indent=2, sort_keys=True), file=stream)
    return 0 if payload["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
