"""Installed CLI for manifest-defined output lease permission auditing."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .output_lease_batch_cli import _load_manifest, _resolve_destinations
from .output_lease_security_batch import inspect_output_lease_permission_batch
from .report_io import write_json_report


def build_parser() -> argparse.ArgumentParser:
    """Build the batch permission-audit command parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-output-lease-permissions-batch",
        description=(
            "Audit permissions for an exact manifest-defined set of AKILAN artifact "
            "output leases without acquiring, repairing, releasing, or removing them."
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
        help="Optional path for deterministic machine-readable permission evidence",
    )
    parser.add_argument(
        "--require-secure",
        action="store_true",
        help="Return failure unless every lease is absent or has verified secure POSIX permissions",
    )
    return parser


def _manifest_failure(path: Path, failure: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize shared manifest-validation evidence for this command."""

    return {
        "status": failure["status"],
        "secure": False,
        "accepted": False,
        "require_secure": False,
        "manifest_path": str(path),
        "destination_count": 0,
        "insecure_count": 0,
        "entries": [],
        "violations": list(failure["violations"]),
    }


def _audit_manifest(manifest_path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    destinations, failure = _resolve_destinations(manifest_path, manifest)
    if failure is not None:
        return _manifest_failure(manifest_path, failure)
    inspection = inspect_output_lease_permission_batch(destinations or {})
    return {**inspection.to_dict(), "manifest_path": str(manifest_path)}


def _accepted(payload: Mapping[str, Any], *, require_secure: bool) -> bool:
    if require_secure:
        return payload.get("secure") is True
    if payload.get("status") == "invalid_destination_set":
        return False
    entries = payload.get("entries", [])
    return all(
        entry.get("inspection", {}).get("status") != "invalid_lease_evidence"
        for entry in entries
        if isinstance(entry, Mapping)
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the manifest-defined batch permission audit."""

    parser = build_parser()
    args = parser.parse_args(argv)
    manifest_path = args.manifest.expanduser().resolve()
    manifest, failure = _load_manifest(manifest_path)
    payload = (
        _manifest_failure(manifest_path, failure)
        if failure is not None
        else _audit_manifest(manifest_path, manifest or {})
    )
    payload["require_secure"] = args.require_secure
    payload["accepted"] = _accepted(payload, require_secure=args.require_secure)

    if args.report is not None:
        try:
            write_json_report(payload, args.report)
        except OSError as exc:
            parser.error(f"unable to write report: {exc.__class__.__name__}")

    stream = sys.stdout if payload["accepted"] else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return 0 if payload["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
