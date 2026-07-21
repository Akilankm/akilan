"""Installed command-line interface for deterministic corpus PDF preflight."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .pdf_preflight_batch import preflight_pdf_batch
from .report_io import write_json_report


def _load_password_map(path: Path | None) -> dict[str, str] | None:
    if path is None:
        return None
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"cannot read password map {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON password map {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit("password map must be a JSON object of source paths to passwords")

    passwords: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not key:
            raise SystemExit("password map keys must be non-empty strings")
        if not isinstance(value, str) or not value:
            raise SystemExit(f"password for {key!r} must be a non-empty string")
        passwords[key] = value
    return passwords


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="akilan-preflight-batch",
        description="Preflight every PDF in a corpus without constructing or modifying artifacts.",
    )
    parser.add_argument("root", type=Path, help="Directory containing PDF sources")
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Inspect only PDFs directly below the root directory",
    )
    parser.add_argument(
        "--password-map",
        type=Path,
        help="UTF-8 JSON object mapping absolute or root-relative PDF paths to passwords",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for the deterministic machine-readable batch report",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    passwords = _load_password_map(args.password_map)
    report = preflight_pdf_batch(
        args.root,
        recursive=not args.no_recursive,
        passwords=passwords,
    )
    report_path: Path | None = None
    if args.report is not None:
        report_path = write_json_report(report.to_dict(), args.report)

    payload = {
        **report.to_dict(),
        "accepted": report.accepted,
        "report": str(report_path) if report_path is not None else None,
    }
    stream = sys.stdout if report.accepted else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return 0 if report.accepted else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
