"""Installed fail-closed benchmark command for exact PDF source sets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .benchmark import write_corpus_report
from .benchmark_acceptance import BenchmarkThresholds, evaluate_corpus
from .benchmark_summary import summarize_corpus_performance
from .config import ExtractionConfig
from .guarded_benchmark import BenchmarkSourceGuardError, run_guarded_corpus_with_report
from .performance_execution_identity import build_performance_execution_identity
from .report_io import write_json_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="akilan-guarded-benchmark",
        description="Preflight an exact PDF corpus before any benchmark artifact or cache is created.",
    )
    parser.add_argument("corpus", type=Path, help="Directory containing benchmark PDFs")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--acceptance-report", type=Path)
    parser.add_argument("--guard-report", type=Path, help="Optional accepted or rejected source evidence report")
    parser.add_argument("--performance-report", type=Path, help="Optional aggregate performance evidence report")
    parser.add_argument(
        "--execution-identity-report",
        type=Path,
        help="Optional runtime and extraction-configuration identity report",
    )
    parser.add_argument("--pattern", default="*.pdf", help="Recursive glob pattern relative to the corpus")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--min-success-rate", type=float, default=1.0)
    parser.add_argument("--min-ordered-element-ratio", type=float, default=1.0)
    parser.add_argument("--min-pages-per-second", type=float, default=0.0)
    parser.add_argument("--max-output-to-source-ratio", type=float)
    parser.add_argument("--max-peak-python-memory-bytes", type=int)
    parser.add_argument("--max-elapsed-seconds", type=float)
    parser.add_argument("--include-characters", action="store_true")
    parser.add_argument("--render-pages", action="store_true")
    parser.add_argument("--render-dpi", type=int, default=144)
    parser.add_argument("--no-tables", action="store_true")
    parser.add_argument("--no-images", action="store_true")
    parser.add_argument("--no-drawings", action="store_true")
    return parser


def _write_guard_report(payload: dict[str, object], path: Path | None) -> str | None:
    if path is None:
        return None
    return str(write_json_report(payload, path))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    corpus = args.corpus.expanduser().resolve()
    if not corpus.is_dir():
        build_parser().error(f"benchmark corpus directory does not exist: {corpus}")

    sources = sorted(path for path in corpus.rglob(args.pattern) if path.is_file())
    try:
        thresholds = BenchmarkThresholds(
            min_success_rate=args.min_success_rate,
            min_ordered_element_ratio=args.min_ordered_element_ratio,
            min_pages_per_second=args.min_pages_per_second,
            max_output_to_source_ratio=args.max_output_to_source_ratio,
            max_peak_python_memory_bytes=args.max_peak_python_memory_bytes,
            max_elapsed_seconds=args.max_elapsed_seconds,
        )
    except ValueError as exc:
        build_parser().error(f"invalid benchmark threshold: {exc}")

    config = ExtractionConfig(
        include_characters=args.include_characters,
        render_pages=args.render_pages,
        render_dpi=args.render_dpi,
        extract_tables=not args.no_tables,
        extract_images=not args.no_images,
        extract_drawings=not args.no_drawings,
        overwrite=True,
    )

    try:
        execution = run_guarded_corpus_with_report(
            sources,
            args.output_root,
            config=config,
            use_cache=not args.no_cache,
        )
    except BenchmarkSourceGuardError as exc:
        guard_payload = exc.report.to_dict()
        payload = {
            **guard_payload,
            "accepted": False,
            "guard_report": _write_guard_report(guard_payload, args.guard_report),
            "performance_report": None,
            "execution_identity_report": None,
        }
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    report = execution.corpus_report
    guard_payload = execution.guard_report.to_dict()
    guard_report_path = _write_guard_report(guard_payload, args.guard_report)
    report_path = write_corpus_report(report, args.report)
    performance = summarize_corpus_performance(report)
    performance_path = (
        write_json_report(performance.to_dict(), args.performance_report)
        if args.performance_report is not None
        else None
    )
    execution_identity = build_performance_execution_identity(config)
    execution_identity_path = (
        write_json_report(execution_identity.to_dict(), args.execution_identity_report)
        if args.execution_identity_report is not None
        else None
    )
    acceptance = evaluate_corpus(report, thresholds)
    acceptance_path = (
        write_json_report(acceptance.to_dict(), args.acceptance_report)
        if args.acceptance_report is not None
        else None
    )
    payload = {
        "report": str(report_path),
        "acceptance_report": str(acceptance_path) if acceptance_path else None,
        "guard_report": guard_report_path,
        "performance_report": str(performance_path) if performance_path else None,
        "execution_identity_report": (
            str(execution_identity_path) if execution_identity_path else None
        ),
        "guard_fingerprint": execution.guard_report.fingerprint,
        "guarded_source_count": execution.guard_report.total_count,
        "execution_identity_fingerprint": execution_identity.fingerprint,
        "total": len(report.cases),
        "succeeded": report.succeeded,
        "failed": report.failed,
        "accepted": acceptance.passed,
        "violation_count": len(acceptance.violations),
        "performance": performance.to_dict(),
        "execution_identity": execution_identity.to_dict(),
    }
    stream = sys.stdout if acceptance.passed else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return 0 if acceptance.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
