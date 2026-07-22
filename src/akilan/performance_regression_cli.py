"""Installed fail-closed gate for corpus performance regressions."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from .benchmark_summary import CorpusPerformanceSummary
from .performance_regression import PerformanceRegressionThresholds, compare_corpus_performance
from .report_io import write_json_report

_REQUIRED_FIELDS = {
    "measured_case_count",
    "cache_hit_count",
    "cache_hit_ratio",
    "total_elapsed_seconds",
    "total_source_size_bytes",
    "total_output_size_bytes",
    "total_page_count",
    "pages_per_second",
    "source_mib_per_second",
    "peak_python_memory_bytes",
    "phase_seconds",
}


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read performance report: {path}") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"performance report is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"performance report root must be a JSON object: {path}")
    return payload


def _number(payload: dict[str, Any], field: str, *, integer: bool = False) -> float | int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int if integer else (int, float)):
        expected = "integer" if integer else "number"
        raise ValueError(f"{field} must be a non-negative finite {expected}")
    if value < 0 or not math.isfinite(float(value)):
        expected = "integer" if integer else "number"
        raise ValueError(f"{field} must be a non-negative finite {expected}")
    return value


def load_performance_summary(path: Path) -> CorpusPerformanceSummary:
    """Load and strictly validate persisted corpus performance evidence."""

    payload = _read_json_object(path)
    missing = sorted(_REQUIRED_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"performance report is missing required fields: {', '.join(missing)}")

    phase_payload = payload["phase_seconds"]
    if not isinstance(phase_payload, dict):
        raise ValueError("phase_seconds must be a JSON object")
    phase_seconds: dict[str, float] = {}
    for name, value in sorted(phase_payload.items()):
        if not isinstance(name, str) or not name:
            raise ValueError("phase_seconds keys must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"phase_seconds.{name} must be a non-negative finite number")
        numeric = float(value)
        if numeric < 0 or not math.isfinite(numeric):
            raise ValueError(f"phase_seconds.{name} must be a non-negative finite number")
        phase_seconds[name] = numeric

    measured_case_count = int(_number(payload, "measured_case_count", integer=True))
    cache_hit_count = int(_number(payload, "cache_hit_count", integer=True))
    cache_hit_ratio = float(_number(payload, "cache_hit_ratio"))
    if cache_hit_count > measured_case_count:
        raise ValueError("cache_hit_count cannot exceed measured_case_count")
    if cache_hit_ratio > 1.0:
        raise ValueError("cache_hit_ratio must be between 0.0 and 1.0")

    return CorpusPerformanceSummary(
        measured_case_count=measured_case_count,
        cache_hit_count=cache_hit_count,
        cache_hit_ratio=cache_hit_ratio,
        total_elapsed_seconds=float(_number(payload, "total_elapsed_seconds")),
        total_source_size_bytes=int(_number(payload, "total_source_size_bytes", integer=True)),
        total_output_size_bytes=int(_number(payload, "total_output_size_bytes", integer=True)),
        total_page_count=int(_number(payload, "total_page_count", integer=True)),
        pages_per_second=float(_number(payload, "pages_per_second")),
        source_mib_per_second=float(_number(payload, "source_mib_per_second")),
        peak_python_memory_bytes=int(_number(payload, "peak_python_memory_bytes", integer=True)),
        phase_seconds=phase_seconds,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the performance-regression command parser."""

    defaults = PerformanceRegressionThresholds()
    parser = argparse.ArgumentParser(
        prog="akilan-performance-regression",
        description=(
            "Compare current corpus performance evidence with an approved equivalent-workload baseline. "
            "The command is read-only and fails closed for malformed or non-equivalent evidence."
        ),
    )
    parser.add_argument("baseline", type=Path, help="Approved baseline performance JSON report")
    parser.add_argument("current", type=Path, help="Current performance JSON report")
    parser.add_argument("--report", type=Path, help="Optional deterministic regression evidence path")
    parser.add_argument(
        "--min-pages-per-second-ratio",
        type=float,
        default=defaults.min_pages_per_second_ratio,
    )
    parser.add_argument(
        "--max-elapsed-seconds-increase-ratio",
        type=float,
        default=defaults.max_elapsed_seconds_increase_ratio,
    )
    parser.add_argument(
        "--max-output-size-increase-ratio",
        type=float,
        default=defaults.max_output_size_increase_ratio,
    )
    parser.add_argument(
        "--max-peak-memory-increase-ratio",
        type=float,
        default=defaults.max_peak_memory_increase_ratio,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the fail-closed performance regression gate."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        baseline = load_performance_summary(args.baseline)
        current = load_performance_summary(args.current)
        thresholds = PerformanceRegressionThresholds(
            min_pages_per_second_ratio=args.min_pages_per_second_ratio,
            max_elapsed_seconds_increase_ratio=args.max_elapsed_seconds_increase_ratio,
            max_output_size_increase_ratio=args.max_output_size_increase_ratio,
            max_peak_memory_increase_ratio=args.max_peak_memory_increase_ratio,
        )
    except ValueError as exc:
        parser.error(str(exc))

    comparison = compare_corpus_performance(current, baseline, thresholds)
    payload = {
        **comparison.to_dict(),
        "baseline": str(args.baseline.resolve()),
        "current": str(args.current.resolve()),
        "report": None,
    }
    if args.report is not None:
        report_path = write_json_report(payload, args.report)
        payload["report"] = str(report_path)
        write_json_report(payload, report_path)

    stream = sys.stdout if comparison.passed else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return 0 if comparison.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
