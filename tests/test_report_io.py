from __future__ import annotations

import json
from pathlib import Path

import pytest

from akilan.report_io import write_json_report


def test_write_json_report_publishes_deterministic_json(tmp_path: Path) -> None:
    destination = tmp_path / "reports" / "acceptance.json"

    result = write_json_report({"z": 1, "label": "café", "a": [2, 1]}, destination)

    assert result == destination.resolve()
    assert destination.read_text(encoding="utf-8") == (
        '{\n  "a": [\n    2,\n    1\n  ],\n  "label": "café",\n  "z": 1\n}\n'
    )
    assert json.loads(destination.read_text(encoding="utf-8"))["label"] == "café"
    assert list(destination.parent.glob(f".{destination.name}.*.tmp")) == []


def test_write_json_report_preserves_existing_report_on_serialization_failure(tmp_path: Path) -> None:
    destination = tmp_path / "report.json"
    destination.write_text('{"status": "previous"}\n', encoding="utf-8")

    with pytest.raises(TypeError):
        write_json_report({"unsupported": object()}, destination)

    assert destination.read_text(encoding="utf-8") == '{"status": "previous"}\n'
    assert list(tmp_path.glob(f".{destination.name}.*.tmp")) == []


def test_write_json_report_cleans_up_when_atomic_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "report.json"
    destination.write_text('{"status": "previous"}\n', encoding="utf-8")

    def fail_replace(source: Path, target: Path) -> None:
        raise OSError(f"cannot replace {source} with {target}")

    monkeypatch.setattr("akilan.report_io.os.replace", fail_replace)

    with pytest.raises(OSError, match="cannot replace"):
        write_json_report({"status": "next"}, destination)

    assert destination.read_text(encoding="utf-8") == '{"status": "previous"}\n'
    assert list(tmp_path.glob(f".{destination.name}.*.tmp")) == []
