"""Installed CLI for read-only artifact output lease permission auditing."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .output_lease_security import inspect_output_build_lease_permissions


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="akilan-output-lease-permissions",
        description=(
            "Audit AKILAN artifact output lease permissions without acquiring, "
            "repairing, releasing, or removing the lease."
        ),
    )
    parser.add_argument("destination", type=Path, help="Artifact output destination protected by the lease")
    parser.add_argument("--report", type=Path, help="Optional path for deterministic JSON audit evidence")
    parser.add_argument(
        "--require-secure",
        action="store_true",
        help="Return failure unless the lease is absent or its POSIX permissions are verified secure",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    inspection = inspect_output_build_lease_permissions(args.destination)
    payload = inspection.to_dict()
    payload["require_secure"] = args.require_secure
    payload["accepted"] = inspection.secure if args.require_secure else inspection.status != "invalid_lease_evidence"

    if args.report is not None:
        try:
            _write_report(args.report, payload)
        except OSError as exc:
            parser.error(f"unable to write report: {exc.__class__.__name__}")

    stream = sys.stdout if payload["accepted"] else sys.stderr
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")
    return 0 if payload["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
