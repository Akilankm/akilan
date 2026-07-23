"""Installed fail-closed CLI for comparing persisted AKILAN benchmark reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .benchmark_comparison import (
    BenchmarkRegressionThresholds,
    compare_benchmark_reports,
    write_benchmark_comparison_report,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone benchmark-comparison parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-compare-benchmarks",
        description="Compare baseline and candidate AKILAN benchmark reports.",
    )
    parser.add_argument("baseline", type=Path, help="Persisted baseline benchmark report")
    parser.add_argument("candidate", type=Path, help="Persisted candidate benchmark report")
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional destination for deterministic machine-readable comparison evidence",
    )
    parser.add_argument("--max-elapsed-increase-ratio", type=float, default=0.0)
    parser.add_argument("--max-memory-increase-ratio", type=float, default=0.0)
    parser.add_argument("--max-throughput-decrease-ratio", type=float, default=0.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the installed benchmark regression gate."""

    args = build_parser().parse_args(argv)
    try:
        thresholds = BenchmarkRegressionThresholds(
            max_elapsed_increase_ratio=args.max_elapsed_increase_ratio,
            max_memory_increase_ratio=args.max_memory_increase_ratio,
            max_throughput_decrease_ratio=args.max_throughput_decrease_ratio,
        )
        comparison = compare_benchmark_reports(args.baseline, args.candidate, thresholds)
    except ValueError as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "error": str(exc),
                    "baseline": str(args.baseline.expanduser().resolve()),
                    "candidate": str(args.candidate.expanduser().resolve()),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    report_path: Path | None = None
    if args.report is not None:
        report_path = write_benchmark_comparison_report(comparison, args.report)

    payload = {
        **comparison.to_dict(),
        "baseline": str(args.baseline.expanduser().resolve()),
        "candidate": str(args.candidate.expanduser().resolve()),
        "report": str(report_path) if report_path is not None else None,
    }
    stream = sys.stdout if comparison.passed else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return 0 if comparison.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
