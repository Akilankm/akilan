from __future__ import annotations

from akilan.cli import build_parser


def test_benchmark_parser_accepts_elapsed_time_budget() -> None:
    args = build_parser().parse_args(
        [
            "benchmark",
            "data",
            "--output-root",
            "artifacts/benchmark",
            "--report",
            "artifacts/benchmark/report.json",
            "--max-elapsed-seconds",
            "30.5",
        ]
    )

    assert args.max_elapsed_seconds == 30.5


def test_benchmark_parser_leaves_elapsed_time_budget_disabled_by_default() -> None:
    args = build_parser().parse_args(
        [
            "benchmark",
            "data",
            "--output-root",
            "artifacts/benchmark",
            "--report",
            "artifacts/benchmark/report.json",
        ]
    )

    assert args.max_elapsed_seconds is None
