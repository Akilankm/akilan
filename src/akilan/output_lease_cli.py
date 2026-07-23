"""Installed CLI for read-only artifact output lease inspection."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .output_lease import inspect_output_build_lease


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="akilan-output-lease",
        description="Inspect an AKILAN artifact output lease without acquiring, releasing, or removing it.",
    )
    parser.add_argument("destination", type=Path, help="Artifact output destination protected by the lease")
    parser.add_argument("--report", type=Path, help="Optional path for deterministic JSON inspection evidence")
    parser.add_argument(
        "--require-absent",
        action="store_true",
        help="Return failure unless no lease is present; malformed or active leases also fail",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    inspection = inspect_output_build_lease(args.destination)
    payload = inspection.to_dict()
    payload["require_absent"] = args.require_absent
    payload["accepted"] = inspection.valid and (not args.require_absent or not inspection.present)

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
