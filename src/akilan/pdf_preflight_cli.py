"""Installed command-line interface for deterministic PDF preflight diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pdf_preflight import preflight_pdf
from .report_io import write_json_report


def _strip_terminal_newline(value: str) -> str:
    if value.endswith("\r\n"):
        return value[:-2]
    if value.endswith(("\n", "\r")):
        return value[:-1]
    return value


def _password_from_args(args: argparse.Namespace) -> str | None:
    if args.password is not None:
        return args.password
    if args.password_file is not None:
        try:
            value = args.password_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise SystemExit(f"cannot read password file {args.password_file}: {exc}") from exc
        password = _strip_terminal_newline(value)
        if not password:
            raise SystemExit(f"password file is empty: {args.password_file}")
        return password
    if args.password_stdin:
        password = _strip_terminal_newline(sys.stdin.readline())
        if not password:
            raise SystemExit("no password was received on standard input")
        return password
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="akilan-preflight",
        description="Inspect a PDF source without constructing or modifying an artifact.",
    )
    parser.add_argument("pdf", type=Path, help="PDF source to inspect")
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for the deterministic machine-readable preflight report",
    )
    password_group = parser.add_mutually_exclusive_group()
    password_group.add_argument(
        "--password",
        help="Encrypted-PDF password (visible to process listings and shell history)",
    )
    password_group.add_argument(
        "--password-file",
        type=Path,
        help="Read the encrypted-PDF password from a UTF-8 file",
    )
    password_group.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read one encrypted-PDF password line from standard input",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = preflight_pdf(args.pdf, password=_password_from_args(args))
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
