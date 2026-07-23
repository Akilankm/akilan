"""Installed fail-closed gate for artifact compatibility and structure."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .artifact_intake import assess_artifact_intake
from .report_io import write_json_report


def build_parser() -> argparse.ArgumentParser:
    """Build the artifact intake command parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-artifact-intake",
        description=(
            "Assess strict schema compatibility and structural validity before "
            "an artifact is consumed. This command never migrates or mutates artifacts."
        ),
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Artifact directory or canonical document.json file",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for deterministic machine-readable intake evidence",
    )
    return parser


def _resolve_document_path(source: Path) -> Path:
    resolved = source.expanduser().resolve()
    return resolved / "document.json" if resolved.is_dir() else resolved


def _source_failure(path: Path, status: str, message: str) -> dict[str, Any]:
    return {
        "accepted": False,
        "source_path": str(path),
        "status": status,
        "message": message,
        "compatibility": None,
        "violation_count": 0,
        "violations": [],
    }


def _load_artifact(path: Path) -> tuple[Mapping[str, Any] | None, dict[str, Any] | None]:
    if not path.exists():
        return None, _source_failure(path, "missing", "artifact document does not exist")
    if not path.is_file():
        return None, _source_failure(path, "not_a_file", "artifact document is not a regular file")

    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, _source_failure(path, "unreadable", "artifact document could not be read as UTF-8")

    try:
        artifact = json.loads(raw)
    except json.JSONDecodeError:
        return None, _source_failure(path, "invalid_json", "artifact document is not valid JSON")

    if not isinstance(artifact, Mapping):
        return None, _source_failure(path, "invalid_root", "artifact JSON root must be an object")
    return artifact, None


def main(argv: list[str] | None = None) -> int:
    """Run the fail-closed artifact intake gate.

    Exit codes:
    - 0: compatible and structurally valid artifact
    - 1: unreadable, incompatible, or structurally invalid artifact
    - 2: invalid command configuration
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    document_path = _resolve_document_path(args.source)
    artifact, failure = _load_artifact(document_path)

    if failure is None:
        assert artifact is not None
        assessment = assess_artifact_intake(artifact)
        payload = {
            **assessment.to_dict(),
            "source_path": str(document_path),
            "status": "accepted" if assessment.accepted else "rejected",
        }
    else:
        payload = failure

    report_path: Path | None = None
    if args.report is not None:
        report_path = write_json_report(payload, args.report)

    output = {
        **payload,
        "report": str(report_path) if report_path is not None else None,
    }
    stream = sys.stdout if payload["accepted"] else sys.stderr
    print(json.dumps(output, indent=2, sort_keys=True), file=stream)
    return 0 if payload["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
