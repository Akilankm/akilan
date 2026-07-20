from __future__ import annotations

from akilan.cli import build_parser


def test_benchmark_parser_accepts_peak_python_memory_budget() -> None:
    args = build_parser().parse_args(
        [
            "benchmark",
            "data",
            "--output-root",
            "artifacts/benchmark",
            "--report",
            "artifacts/benchmark/report.json",
            "--max-peak-python-memory-bytes",
            "268435456",
        ]
    )

    assert args.max_peak_python_memory_bytes == 268435456


def test_benchmark_parser_leaves_memory_budget_disabled_by_default() -> None:
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

    assert args.max_peak_python_memory_bytes is None
