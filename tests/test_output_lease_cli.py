from __future__ import annotations

import json
from pathlib import Path

from akilan.output_lease import OutputBuildLease
from akilan.output_lease_cli import main


def _read_stream(capsys: object, *, stderr: bool = False) -> dict[str, object]:
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    return json.loads(captured.err if stderr else captured.out)


def test_absent_lease_is_accepted_by_default(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"

    assert main([str(destination)]) == 0

    payload = _read_stream(capsys)
    assert payload["status"] == "absent"
    assert payload["present"] is False
    assert payload["valid"] is True
    assert payload["require_absent"] is False
    assert payload["accepted"] is True


def test_active_valid_lease_is_visible_without_mutation(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination).acquire()
    try:
        assert main([str(destination)]) == 0
        payload = _read_stream(capsys)
        assert payload["status"] == "valid"
        assert payload["present"] is True
        assert payload["accepted"] is True
        assert Path(payload["lease_path"]).is_dir()
    finally:
        lease.release()


def test_require_absent_rejects_active_valid_lease(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination).acquire()
    try:
        assert main([str(destination), "--require-absent"]) == 1
        payload = _read_stream(capsys, stderr=True)
        assert payload["status"] == "valid"
        assert payload["require_absent"] is True
        assert payload["accepted"] is False
    finally:
        lease.release()


def test_invalid_lease_evidence_fails_closed(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"
    lease_path = tmp_path / ".artifact.akilan.lock"
    lease_path.mkdir()
    (lease_path / "owner.json").write_text("not-json", encoding="utf-8")

    assert main([str(destination)]) == 1

    payload = _read_stream(capsys, stderr=True)
    assert payload["status"] == "invalid_owner_evidence"
    assert payload["valid"] is False
    assert payload["accepted"] is False


def test_report_matches_emitted_payload(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"
    report = tmp_path / "reports" / "lease.json"

    assert main([str(destination), "--require-absent", "--report", str(report)]) == 0

    emitted = _read_stream(capsys)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert persisted == emitted
