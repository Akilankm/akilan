from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from akilan.output_lease import OutputBuildLease
from akilan.output_lease_security_cli import main


def _read_stream(capsys: object, *, stderr: bool = False) -> dict[str, object]:
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    return json.loads(captured.err if stderr else captured.out)


def test_absent_lease_is_secure_and_accepted(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"

    assert main([str(destination), "--require-secure"]) == 0

    payload = _read_stream(capsys)
    assert payload["status"] == "absent"
    assert payload["secure"] is True
    assert payload["require_secure"] is True
    assert payload["accepted"] is True


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode-bit contract")
def test_secure_active_lease_is_accepted(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination).acquire()
    try:
        Path(lease.path).chmod(0o700)
        (Path(lease.path) / "owner.json").chmod(0o600)

        assert main([str(destination), "--require-secure"]) == 0
        payload = _read_stream(capsys)
        assert payload["status"] == "secure"
        assert payload["lease_mode"] == "0700"
        assert payload["owner_mode"] == "0600"
        assert payload["accepted"] is True
    finally:
        lease.release()


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode-bit contract")
def test_require_secure_rejects_insecure_owner_permissions(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination).acquire()
    try:
        owner_path = Path(lease.path) / "owner.json"
        owner_path.chmod(0o666)

        assert main([str(destination), "--require-secure"]) == 1
        payload = _read_stream(capsys, stderr=True)
        assert payload["status"] == "insecure_permissions"
        assert payload["secure"] is False
        assert payload["accepted"] is False
        assert "owner_json_must_not_be_group_or_world_writable" in payload["violations"]
    finally:
        owner_path.chmod(0o600)
        lease.release()


def test_invalid_structural_evidence_fails_even_without_policy_gate(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"
    lease_path = tmp_path / ".artifact.akilan.lock"
    lease_path.mkdir()
    (lease_path / "owner.json").write_text("not-json", encoding="utf-8")

    assert main([str(destination)]) == 1

    payload = _read_stream(capsys, stderr=True)
    assert payload["status"] == "invalid_lease_evidence"
    assert payload["accepted"] is False


def test_report_matches_emitted_payload(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"
    report = tmp_path / "reports" / "permission-audit.json"

    assert main([str(destination), "--require-secure", "--report", str(report)]) == 0

    emitted = _read_stream(capsys)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert persisted == emitted
