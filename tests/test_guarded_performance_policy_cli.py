from __future__ import annotations

import json
from pathlib import Path

import pytest

from akilan.canonical_json import canonical_json_fingerprint
from akilan.guarded_performance_policy_cli import main


def _write_regression_evidence(path: Path, *, passed: bool = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "passed": passed,
        "violations": [] if passed else [{"rule": "throughput"}],
    }
    evidence = {**payload, "evidence_fingerprint": canonical_json_fingerprint(payload)}
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return evidence


def test_cli_creates_tamper_evident_policy_evidence(tmp_path: Path, capsys) -> None:
    source = tmp_path / "regression.json"
    _write_regression_evidence(source)
    report = tmp_path / "policy.json"

    assert main([str(source), "--report", str(report), "--require-passed"]) == 0

    output = json.loads(capsys.readouterr().out)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert output["decision_accepted"] is True
    assert output["operational_status"] == "accepted"
    assert persisted == {key: value for key, value in output.items() if key not in {"report", "source"}}
    fingerprint = persisted.pop("policy_evidence_fingerprint")
    assert fingerprint == canonical_json_fingerprint(persisted)


def test_cli_persists_authentic_rejected_policy_evidence(tmp_path: Path, capsys) -> None:
    source = tmp_path / "regression.json"
    _write_regression_evidence(source, passed=False)
    report = tmp_path / "policy.json"

    assert main([str(source), "--report", str(report), "--require-passed"]) == 1

    output = json.loads(capsys.readouterr().err)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert output["decision_accepted"] is False
    assert output["operational_status"] == "recorded_decision_failed"
    assert persisted["decision_accepted"] is False
    assert len(persisted["policy_evidence_fingerprint"]) == 64


def test_cli_rejects_tampered_regression_evidence(tmp_path: Path, capsys) -> None:
    source = tmp_path / "regression.json"
    evidence = _write_regression_evidence(source)
    evidence["passed"] = False
    source.write_text(json.dumps(evidence), encoding="utf-8")
    report = tmp_path / "policy.json"

    assert main([str(source), "--report", str(report), "--require-passed"]) == 1

    output = json.loads(capsys.readouterr().err)
    assert output["decision_accepted"] is False
    assert output["operational_status"] == "fingerprint_mismatch"
    assert report.exists()


def test_cli_rejects_missing_source_without_report_side_effect(tmp_path: Path, capsys) -> None:
    source = tmp_path / "missing.json"
    report = tmp_path / "policy.json"

    assert main([str(source), "--report", str(report)]) == 1

    output = json.loads(capsys.readouterr().err)
    assert output["status"] == "missing"
    assert output["decision_accepted"] is False
    assert not report.exists()


def test_cli_rejects_overwriting_source(tmp_path: Path) -> None:
    source = tmp_path / "regression.json"
    _write_regression_evidence(source)

    with pytest.raises(SystemExit) as exc_info:
        main([str(source), "--report", str(source)])

    assert exc_info.value.code == 2
