"""Installed CLI for complete artifact-directory integrity evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .artifact_directory_integrity import assess_artifact_directory_integrity


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="akilan-artifact-integrity",
        description="Generate fail-closed byte-integrity evidence for a complete AKILAN artifact directory.",
    )
    parser.add_argument("artifact_root", type=Path, help="Artifact directory containing document.json")
    parser.add_argument("--report", type=Path, help="Optional path for deterministic JSON evidence")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = assess_artifact_directory_integrity(args.artifact_root)
    payload = report.to_dict()

    if args.report is not None:
        try:
            _write_report(args.report, payload)
        except OSError as exc:
            build_parser().error(f"unable to write report: {exc.__class__.__name__}")

    stream = sys.stdout if report.accepted else sys.stderr
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
