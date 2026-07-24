from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from akilan.output_lease import OutputBuildLease
from akilan.output_lease_security_batch_cli import main


def _write_manifest(path: Path, destinations: dict[str, str]) -> None:
    path.write_text(json.dumps(destinations), encoding="utf-8")


def _read_stream(capsys: object, *, stderr: bool = False) -> dict[str, object]:
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    return json.loads(captured.err if stderr else captured.out)


def test_absent_manifest_destinations_are_secure(tmp_path: Path, capsys: object) -> None:
    manifest = tmp_path / "destinations.json"
    _write_manifest(manifest, {"beta": "outputs/beta", "alpha": "outputs/alpha"})

    assert main([str(manifest), "--require-secure"]) == 0

    payload = _read_stream(capsys)
    assert payload["status"] == "secure"
    assert payload["secure"] is True
    assert payload["accepted"] is True
    assert [entry["identifier"] for entry in payload["entries"]] == ["alpha", "beta"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode-bit contract")
def test_require_secure_rejects_any_insecure_destination(tmp_path: Path, capsys: object) -> None:
    secure_destination = tmp_path / "secure"
    insecure_destination = tmp_path / "insecure"
    manifest = tmp_path / "destinations.json"
    _write_manifest(
        manifest,
        {"secure": str(secure_destination), "insecure": str(insecure_destination)},
    )
    secure_lease = OutputBuildLease(secure_destination).acquire()
    insecure_lease = OutputBuildLease(insecure_destination).acquire()
    insecure_owner = Path(insecure_lease.path) / "owner.json"
    try:
        Path(secure_lease.path).chmod(0o700)
        (Path(secure_lease.path) / "owner.json").chmod(0o600)
        Path(insecure_lease.path).chmod(0o700)
        insecure_owner.chmod(0o666)

        assert main([str(manifest), "--require-secure"]) == 1
        payload = _read_stream(capsys, stderr=True)
        assert payload["status"] == "insecure"
        assert payload["secure"] is False
        assert payload["insecure_count"] == 1
        assert payload["accepted"] is False
    finally:
        insecure_owner.chmod(0o600)
        insecure_lease.release()
        secure_lease.release()


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode-bit contract")
def test_observability_mode_reports_insecure_permissions_without_policy_failure(
    tmp_path: Path,
    capsys: object,
) -> None:
    destination = tmp_path / "artifact"
    manifest = tmp_path / "destinations.json"
    _write_manifest(manifest, {"artifact": str(destination)})
    lease = OutputBuildLease(destination).acquire()
    owner_path = Path(lease.path) / "owner.json"
    try:
        owner_path.chmod(0o666)

        assert main([str(manifest)]) == 0
        payload = _read_stream(capsys)
        assert payload["status"] == "insecure"
        assert payload["secure"] is False
        assert payload["accepted"] is True
    finally:
        owner_path.chmod(0o600)
        lease.release()


def test_invalid_structural_evidence_fails_without_policy_gate(tmp_path: Path, capsys: object) -> None:
    destination = tmp_path / "artifact"
    manifest = tmp_path / "destinations.json"
    _write_manifest(manifest, {"artifact": str(destination)})
    lease_path = tmp_path / ".artifact.akilan.lock"
    lease_path.mkdir()
    (lease_path / "owner.json").write_text("not-json", encoding="utf-8")

    assert main([str(manifest)]) == 1

    payload = _read_stream(capsys, stderr=True)
    assert payload["status"] == "insecure"
    assert payload["accepted"] is False


def test_relative_destinations_resolve_from_manifest_directory(tmp_path: Path, capsys: object) -> None:
    manifest_directory = tmp_path / "config"
    manifest_directory.mkdir()
    manifest = manifest_directory / "destinations.json"
    _write_manifest(manifest, {"artifact": "../outputs/artifact"})

    assert main([str(manifest), "--require-secure"]) == 0

    payload = _read_stream(capsys)
    destination = payload["entries"][0]["inspection"]["destination"]
    assert destination == str((tmp_path / "outputs" / "artifact").resolve())


def test_report_matches_emitted_payload(tmp_path: Path, capsys: object) -> None:
    manifest = tmp_path / "destinations.json"
    report = tmp_path / "reports" / "permission-batch.json"
    _write_manifest(manifest, {"artifact": "outputs/artifact"})

    assert main([str(manifest), "--require-secure", "--report", str(report)]) == 0

    emitted = _read_stream(capsys)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert persisted == emitted
