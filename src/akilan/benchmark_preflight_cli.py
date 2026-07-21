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
        "--report",
        type=Path,
        help="Optional path for deterministic machine-readable preflight evidence",
    )
    return parser


def _build_report(corpus: Path, pattern: str) -> dict[str, Any]:
    root = corpus.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"benchmark corpus directory does not exist: {root}")

    sources = tuple(sorted((path.resolve() for path in root.rglob(pattern) if path.is_file()), key=str))
    entries = [preflight_pdf(path).to_dict() for path in sources]
    accepted_count = sum(bool(entry["accepted"]) for entry in entries)
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
    args = build_parser().parse_args(argv)
    try:
        report = _build_report(args.corpus, args.pattern)
    except ValueError as exc:
        build_parser().error(str(exc))

    if args.report is not None:
        report_path = write_json_report(report, args.report)
        report = {**report, "report": str(report_path)}
    else:
        report = {**report, "report": None}

    stream = sys.stdout if report["accepted"] else sys.stderr
    print(json.dumps(report, indent=2, sort_keys=True), file=stream)
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
