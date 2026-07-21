from __future__ import annotations

import json

import pytest

from akilan.schema import SUPPORTED_SCHEMA_MAJOR
from akilan.schema_compatibility_cli import main


def test_compatible_version_returns_zero_and_writes_report(tmp_path, capsys) -> None:
    report_path = tmp_path / "compatibility.json"

    exit_code = main(
        [
            f"{SUPPORTED_SCHEMA_MAJOR}.9.4",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["compatible"] is True
    assert payload["status"] == "compatible"
    assert payload["report"] == str(report_path.resolve())
    assert persisted["compatible"] is True
    assert persisted["parsed_version"] == f"{SUPPORTED_SCHEMA_MAJOR}.9.4"


def test_unsupported_major_fails_closed_on_stderr(capsys) -> None:
    exit_code = main([f"{SUPPORTED_SCHEMA_MAJOR + 1}.0.0"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["compatible"] is False
    assert payload["status"] == "unsupported_major"
    assert payload["next_step"].startswith("reject the artifact")


def test_invalid_version_fails_closed(capsys) -> None:
    exit_code = main(["v1.2.3"])

    payload = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert payload["status"] == "invalid"
    assert payload["parsed_version"] is None


def test_invalid_supported_major_is_configuration_error(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["1.0.0", "--supported-major", "-1"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "supported_major must be a non-negative integer" in captured.err
