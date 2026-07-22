from __future__ import annotations

import json
from pathlib import Path

from akilan.canonical_json import canonical_json_fingerprint
from akilan.guarded_performance_policy_evidence_cli import main


def _write_policy_evidence(
    path: Path,
    *,
    decision_accepted: bool | None = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "valid": True,
        "status": "valid",
        "require_passed": True,
        "recorded_decision": decision_accepted,
        "operational_status": "accepted" if decision_accepted else "recorded_decision_failed",
    }
    if decision_accepted is not None:
        payload["decision_accepted"] = decision_accepted
    evidence = {
        **payload,
        "policy_evidence_fingerprint": canonical_json_fingerprint(payload),
    }
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return evidence


def test_cli_accepts_valid_policy_evidence_and_persists_verification(
    tmp_path: Path,
    capsys,
) -> None:
    evidence_path = tmp_path / "policy.json"
    _write_policy_evidence(evidence_path, decision_accepted=False)
    report_path = tmp_path / "verification.json"

    exit_code = main([str(evidence_path), "--report", str(report_path)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert output["operational_status"] == "valid"
    assert output["recorded_decision_accepted"] is False
    assert output["operationally_accepted"] is True
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted == {
        key: value for key, value in output.items() if key not in {"report", "source"}
    }


def test_cli_require_accepted_accepts_recorded_acceptance(
    tmp_path: Path,
    capsys,
) -> None:
    evidence_path = tmp_path / "accepted.json"
    _write_policy_evidence(evidence_path, decision_accepted=True)

    assert main([str(evidence_path), "--require-accepted"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert output["operational_status"] == "accepted"
    assert output["require_accepted"] is True
    assert output["recorded_decision_accepted"] is True
    assert output["operationally_accepted"] is True


def test_cli_require_accepted_rejects_recorded_policy_rejection(
    tmp_path: Path,
    capsys,
) -> None:
    evidence_path = tmp_path / "rejected.json"
    _write_policy_evidence(evidence_path, decision_accepted=False)

    assert main([str(evidence_path), "--require-accepted"]) == 1
    output = json.loads(capsys.readouterr().err)
    assert output["valid"] is True
    assert output["operational_status"] == "recorded_policy_rejected"
    assert output["recorded_decision_accepted"] is False
    assert output["operationally_accepted"] is False


def test_cli_require_accepted_rejects_missing_boolean_decision(
    tmp_path: Path,
    capsys,
) -> None:
    evidence_path = tmp_path / "missing-decision.json"
    _write_policy_evidence(evidence_path, decision_accepted=None)

    assert main([str(evidence_path), "--require-accepted"]) == 1
    output = json.loads(capsys.readouterr().err)
    assert output["valid"] is True
    assert output["operational_status"] == "recorded_policy_decision_missing"
    assert output["recorded_decision_accepted"] is None
    assert output["operationally_accepted"] is False


def test_cli_rejects_tampered_policy_evidence(tmp_path: Path, capsys) -> None:
    evidence_path = tmp_path / "tampered.json"
    evidence = _write_policy_evidence(evidence_path, decision_accepted=True)
    evidence["decision_accepted"] = False
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    assert main([str(evidence_path)]) == 1
    output = json.loads(capsys.readouterr().err)
    assert output["valid"] is False
    assert output["status"] == "policy_fingerprint_mismatch"
    assert output["operationally_accepted"] is False


def test_cli_rejects_missing_and_non_object_evidence(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing.json"
    assert main([str(missing)]) == 1
    missing_output = json.loads(capsys.readouterr().err)
    assert missing_output["status"] == "missing"
    assert missing_output["operationally_accepted"] is False

    invalid_root = tmp_path / "array.json"
    invalid_root.write_text("[]", encoding="utf-8")
    assert main([str(invalid_root)]) == 1
    invalid_output = json.loads(capsys.readouterr().err)
    assert invalid_output["status"] == "invalid_root"
    assert invalid_output["operationally_accepted"] is False
