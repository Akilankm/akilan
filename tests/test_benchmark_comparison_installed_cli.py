from __future__ import annotations

import json
from pathlib import Path

from akilan.benchmark_comparison_cli import build_parser, main


def _write_report(path: Path, *, elapsed: float) -> None:
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "source": "sample.pdf",
                        "status": "passed",
                        "elapsed_seconds": elapsed,
                        "performance": {
                            "peak_python_memory_bytes": 100,
                            "pages_per_second": 4.0,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_parser_uses_installed_command_name() -> None:
    assert build_parser().prog == "akilan-compare-benchmarks"


def test_installed_cli_writes_passing_report(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    output = tmp_path / "comparison.json"
    _write_report(baseline, elapsed=10.0)
    _write_report(candidate, elapsed=10.5)

    result = main(
        [
            str(baseline),
            str(candidate),
            "--report",
            str(output),
            "--max-elapsed-increase-ratio",
            "0.06",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    assert json.loads(captured.out)["passed"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_installed_cli_fails_closed_for_invalid_report(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline.write_text("{}", encoding="utf-8")
    candidate.write_text("{}", encoding="utf-8")

    result = main([str(baseline), str(candidate)])

    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "cases array" in json.loads(captured.err)["error"]
