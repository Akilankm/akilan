from __future__ import annotations

import json
from pathlib import Path

import pytest

from akilan.performance_regression_cli import load_performance_summary, main


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "measured_case_count": 2,
        "cache_hit_count": 0,
        "cache_hit_ratio": 0.0,
        "total_elapsed_seconds": 10.0,
        "total_source_size_bytes": 2_000,
        "total_output_size_bytes": 8_000,
        "total_page_count": 20,
        "pages_per_second": 2.0,
        "source_mib_per_second": 0.000191,
        "peak_python_memory_bytes": 1_000,
        "phase_seconds": {"extract": 8.0, "persist": 2.0},
    }
    payload.update(overrides)
    return payload


def _write(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_loader_rejects_missing_and_invalid_fields(tmp_path: Path) -> None:
    missing = _payload()
    del missing["pages_per_second"]
    with pytest.raises(ValueError, match="missing required fields: pages_per_second"):
        load_performance_summary(_write(tmp_path / "missing.json", missing))

    with pytest.raises(ValueError, match="cache_hit_count cannot exceed measured_case_count"):
        load_performance_summary(
            _write(tmp_path / "invalid.json", _payload(measured_case_count=1, cache_hit_count=2))
        )


def test_cli_passes_equivalent_run_and_persists_identical_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    baseline = _write(tmp_path / "baseline.json", _payload())
    current = _write(
        tmp_path / "current.json",
        _payload(total_elapsed_seconds=11.0, total_output_size_bytes=9_000, pages_per_second=1.8),
    )
    report = tmp_path / "regression.json"

    exit_code = main([str(baseline), str(current), "--report", str(report)])

    assert exit_code == 0
    emitted = json.loads(capsys.readouterr().out)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert emitted == persisted
    assert emitted["passed"] is True
    assert emitted["violation_count"] == 0
    assert emitted["report"] == str(report.resolve())


def test_cli_reports_regression_to_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    baseline = _write(tmp_path / "baseline.json", _payload())
    current = _write(
        tmp_path / "current.json",
        _payload(
            total_elapsed_seconds=13.0,
            total_output_size_bytes=11_000,
            pages_per_second=1.5,
            peak_python_memory_bytes=1_400,
        ),
    )

    exit_code = main([str(baseline), str(current)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["passed"] is False
    assert [item["metric"] for item in payload["violations"]] == [
        "pages_per_second",
        "peak_python_memory_bytes",
        "total_elapsed_seconds",
        "total_output_size_bytes",
    ]


def test_cli_rejects_malformed_evidence_as_configuration_error(tmp_path: Path) -> None:
    baseline = _write(tmp_path / "baseline.json", _payload())
    malformed = tmp_path / "current.json"
    malformed.write_text("not-json", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        main([str(baseline), str(malformed)])

    assert exc_info.value.code == 2
