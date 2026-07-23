"""Fail-closed preflight gate for benchmark corpora."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .canonical_json import canonical_json_fingerprint
from .pdf_preflight import preflight_pdf
from .report_io import write_json_report


def _load_password_map(path: Path | None) -> dict[str, str] | None:
    if path is None:
        return None
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read password map {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON password map {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("password map must be a JSON object of source paths to passwords")

    passwords: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not key:
            raise ValueError("password map keys must be non-empty strings")
        if not isinstance(value, str) or not value:
            raise ValueError(f"password for {key!r} must be a non-empty string")
        passwords[key] = value
    return passwords


def _password_for_source(source: Path, root: Path, passwords: dict[str, str] | None) -> str | None:
    if passwords is None:
        return None
    absolute_key = str(source)
    relative_key = source.relative_to(root).as_posix()
    return passwords.get(absolute_key, passwords.get(relative_key))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="akilan-benchmark-preflight",
        description="Validate benchmark PDF inputs before extraction publishes benchmark artifacts.",
    )
    parser.add_argument("corpus", type=Path, help="Directory containing benchmark PDFs")
    parser.add_argument(
        "--pattern",
        default="*.pdf",
        help="Recursive glob pattern relative to the corpus directory",
    )
    parser.add_argument(
        "--password-map",
        type=Path,
        help="UTF-8 JSON object mapping absolute or corpus-relative PDF paths to passwords",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for deterministic machine-readable preflight evidence",
    )
    return parser


def _build_report(
    corpus: Path,
    pattern: str,
    *,
    passwords: dict[str, str] | None = None,
) -> dict[str, Any]:
    root = corpus.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"benchmark corpus directory does not exist: {root}")

    sources = tuple(sorted((path.resolve() for path in root.rglob(pattern) if path.is_file()), key=str))
    reports = [
        preflight_pdf(path, password=_password_for_source(path, root, passwords))
        for path in sources
    ]
    entries = [{**report.to_dict(), "accepted": report.accepted} for report in reports]
    accepted_count = sum(report.accepted for report in reports)
    rejected_count = len(entries) - accepted_count
    status_counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry["status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    evidence = {
        "corpus": str(root),
        "pattern": pattern,
        "total_count": len(entries),
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "status_counts": dict(sorted(status_counts.items())),
        "entries": entries,
    }
    evidence["accepted"] = len(entries) > 0 and rejected_count == 0
    evidence["fingerprint"] = canonical_json_fingerprint(evidence)
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        passwords = _load_password_map(args.password_map)
        report = _build_report(args.corpus, args.pattern, passwords=passwords)
    except ValueError as exc:
        parser.error(str(exc))

    if args.report is not None:
        report_path = write_json_report(report, args.report)
        report = {**report, "report": str(report_path)}
    else:
        report = {**report, "report": None}

    stream = sys.stdout if report["accepted"] else sys.stderr
    print(json.dumps(report, indent=2, sort_keys=True), file=stream)
    return 0 if report["accepted"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
