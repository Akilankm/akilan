from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from akilan.output_lease import OutputBuildLease, OutputLeaseError, inspect_output_build_lease


def _valid_owner(destination: Path) -> dict[str, object]:
    return {
        "token": uuid4().hex,
        "process_id": 123,
        "hostname": "test-host",
        "acquired_at_utc": "2026-07-24T10:00:00+00:00",
        "destination": str(destination.resolve()),
    }


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="requires no-follow descriptor support")
def test_inspection_never_follows_owner_evidence_symlink(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    lease_path = tmp_path / ".artifact.akilan.lock"
    lease_path.mkdir()
    external = tmp_path / "external-owner.json"
    external_payload = json.dumps(_valid_owner(destination)).encode()
    external.write_bytes(external_payload)
    (lease_path / "owner.json").symlink_to(external)

    inspection = inspect_output_build_lease(destination)

    assert inspection.status == "invalid_owner_evidence"
    assert inspection.owner is None
    assert inspection.violations == ("owner_json_must_be_a_regular_file",)
    assert external.read_bytes() == external_payload


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires POSIX FIFO support")
def test_inspection_rejects_fifo_owner_evidence_without_blocking(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    lease_path = tmp_path / ".artifact.akilan.lock"
    lease_path.mkdir()
    owner_path = lease_path / "owner.json"
    os.mkfifo(owner_path)

    inspection = inspect_output_build_lease(destination)

    assert inspection.status == "invalid_owner_evidence"
    assert inspection.owner is None
    assert inspection.violations == ("owner_json_must_be_a_regular_file",)
    assert owner_path.exists()


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="requires no-follow descriptor support")
def test_competing_acquisition_does_not_follow_owner_symlink(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    lease_path = tmp_path / ".artifact.akilan.lock"
    lease_path.mkdir()
    external = tmp_path / "external-owner.json"
    external_payload = json.dumps(_valid_owner(destination)).encode()
    external.write_bytes(external_payload)
    (lease_path / "owner.json").symlink_to(external)

    with pytest.raises(OutputLeaseError, match="already leased"):
        OutputBuildLease(destination).acquire()

    assert external.read_bytes() == external_payload
    assert lease_path.is_dir()
