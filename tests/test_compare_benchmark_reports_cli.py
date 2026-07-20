from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "compare_benchmark_reports.py"
SPEC = importlib.util.spec_from_file_location("compare_benchmark_reports_cli", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_report(path: Path, *, elapsed: float, memory: int, throughput: float) -> None:
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "source": "sample.pdf",
                        "status": "passed",
                        "elapsed_seconds": elapsed,
                        "performance": {
                            "peak_python_memory_bytes": memory,
                            "pages_per_second": throughput,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_main_writes_passing_report(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    output = tmp_path / "comparison.json"
    _write_report(baseline, elapsed=10.0, memory=100, throughput=4.0)
    _write_report(candidate, elapsed=10.5, memory=105, throughput=3.9)

    result = MODULE.main(
        [
            str(baseline),
            str(candidate),
            "--report",
            str(output),
            "--max-elapsed-increase-ratio",
            "0.06",
            "--max-memory-increase-ratio",
            "0.06",
            "--max-throughput-decrease-ratio",
            "0.03",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    assert json.loads(captured.out)["passed"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_main_reports_regression_to_stderr(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write_report(baseline, elapsed=10.0, memory=100, throughput=4.0)
    _write_report(candidate, elapsed=12.0, memory=100, throughput=4.0)

    result = MODULE.main([str(baseline), str(candidate), "--max-elapsed-increase-ratio", "0.10"])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert result == 1
    assert captured.out == ""
    assert payload["passed"] is False
    assert payload["regressions"][0]["rule_id"] == "benchmark-elapsed-regression-v1"


def test_main_fails_closed_for_invalid_report(tmp_path: Path, capsys) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    baseline.write_text("{}", encoding="utf-8")
    candidate.write_text("{}", encoding="utf-8")

    result = MODULE.main([str(baseline), str(candidate)])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert result == 2
    assert captured.out == ""
    assert payload["passed"] is False
    assert "cases array" in payload["error"]
