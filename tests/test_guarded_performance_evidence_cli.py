from __future__ import annotations

import json
from pathlib import Path

from akilan.canonical_json import canonical_json_fingerprint
from akilan.guarded_performance_evidence_cli import main


def _write_evidence(
    path: Path,
    *,
    passed: bool | None = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "violation_count": 0 if passed is not False else 1,
        "violations": [] if passed is not False else [{"rule_id": "example"}],
    }
    if passed is not None:
        payload["passed"] = passed
    evidence = {**payload, "evidence_fingerprint": canonical_json_fingerprint(payload)}
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return evidence


def test_cli_accepts_valid_evidence_and_persists_verification(
    tmp_path: Path,
    capsys,
) -> None:
    evidence_path = tmp_path / "decision.json"
    _write_evidence(evidence_path, passed=False)
    report_path = tmp_path / "verification.json"

    exit_code = main([str(evidence_path), "--report", str(report_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert output["status"] == "valid"
    assert output["operational_status"] == "valid"
    assert output["recorded_decision"] is False
    assert output["decision_accepted"] is True
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["valid"] is True
    assert persisted["decision_accepted"] is True


def test_cli_rejects_tampered_evidence(tmp_path: Path, capsys) -> None:
    evidence_path = tmp_path / "decision.json"
    evidence = _write_evidence(evidence_path)
    evidence["passed"] = False
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    exit_code = main([str(evidence_path)])

    assert exit_code == 1
    output = json.loads(capsys.readouterr().err)
    assert output["valid"] is False
    assert output["status"] == "fingerprint_mismatch"
    assert output["decision_accepted"] is False


def test_cli_rejects_missing_or_non_object_evidence(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing.json"
    assert main([str(missing)]) == 1
    missing_output = json.loads(capsys.readouterr().err)
    assert missing_output["status"] == "missing"
    assert missing_output["decision_accepted"] is False

    invalid_root = tmp_path / "array.json"
    invalid_root.write_text("[]", encoding="utf-8")
    assert main([str(invalid_root)]) == 1
    invalid_output = json.loads(capsys.readouterr().err)
    assert invalid_output["status"] == "invalid_root"
    assert invalid_output["decision_accepted"] is False


def test_cli_does_not_treat_recorded_failure_as_invalid_integrity(
    tmp_path: Path,
    capsys,
) -> None:
    evidence_path = tmp_path / "failed-decision.json"
    _write_evidence(evidence_path, passed=False)

    assert main([str(evidence_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert output["recorded_decision"] is False
    assert output["decision_accepted"] is True


def test_cli_require_passed_accepts_recorded_success(
    tmp_path: Path,
    capsys,
) -> None:
    evidence_path = tmp_path / "passed-decision.json"
    _write_evidence(evidence_path, passed=True)

    assert main([str(evidence_path), "--require-passed"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert output["operational_status"] == "accepted"
    assert output["require_passed"] is True
    assert output["recorded_decision"] is True
    assert output["decision_accepted"] is True


def test_cli_require_passed_rejects_recorded_failure_and_persists_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    evidence_path = tmp_path / "failed-decision.json"
    _write_evidence(evidence_path, passed=False)
    report_path = tmp_path / "verification.json"

    assert (
        main(
            [
                str(evidence_path),
                "--require-passed",
                "--report",
                str(report_path),
            ]
        )
        == 1
    )
    output = json.loads(capsys.readouterr().err)
    assert output["valid"] is True
    assert output["operational_status"] == "recorded_decision_failed"
    assert output["recorded_decision"] is False
    assert output["decision_accepted"] is False
    assert json.loads(report_path.read_text(encoding="utf-8")) == {
        key: value
        for key, value in output.items()
        if key not in {"report", "source"}
    }


def test_cli_require_passed_rejects_missing_boolean_decision(
    tmp_path: Path,
    capsys,
) -> None:
    evidence_path = tmp_path / "missing-decision.json"
    _write_evidence(evidence_path, passed=None)

    assert main([str(evidence_path), "--require-passed"]) == 1
    output = json.loads(capsys.readouterr().err)
    assert output["valid"] is True
    assert output["operational_status"] == "recorded_decision_missing"
    assert output["recorded_decision"] is None
    assert output["decision_accepted"] is False
