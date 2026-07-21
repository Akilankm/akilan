"""Installed command-line gate for artifact schema-version compatibility."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report_io import write_json_report
from .schema import SUPPORTED_SCHEMA_MAJOR
from .schema_compatibility import assess_schema_compatibility


def build_parser() -> argparse.ArgumentParser:
    """Build the schema compatibility command parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-schema-compatibility",
        description=(
            "Classify an artifact schema version before structural validation. "
            "This command never migrates or mutates artifacts."
        ),
    )
    parser.add_argument("version", help="Artifact schema version in strict major.minor.patch form")
    parser.add_argument(
        "--supported-major",
        type=int,
        default=SUPPORTED_SCHEMA_MAJOR,
        help=f"Supported schema major (default: {SUPPORTED_SCHEMA_MAJOR})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for deterministic machine-readable compatibility evidence",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the fail-closed compatibility gate.

    Exit codes:
    - 0: compatible schema major
    - 1: invalid version or unsupported schema major
    - 2: invalid command configuration
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        compatibility = assess_schema_compatibility(
            args.version,
            supported_major=args.supported_major,
        )
    except ValueError as exc:
        parser.error(str(exc))

    report_path: Path | None = None
    if args.report is not None:
        report_path = write_json_report(compatibility.to_dict(), args.report)

    payload = {
        **compatibility.to_dict(),
        "report": str(report_path) if report_path is not None else None,
        "next_step": (
            "run structural artifact validation before consumption"
            if compatibility.compatible
            else "reject the artifact or use an explicitly approved migration path"
        ),
    }
    stream = sys.stdout if compatibility.compatible else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return 0 if compatibility.compatible else 1


if __name__ == "__main__":
    raise SystemExit(main())
