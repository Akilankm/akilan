from __future__ import annotations

from pathlib import Path

import pytest

from akilan.output_lease import OutputBuildLease, OutputLeaseError, inspect_output_build_lease


def test_inspection_rejects_oversized_owner_evidence_without_mutation(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    lease_path = tmp_path / ".artifact.akilan.lock"
    lease_path.mkdir()
    owner_path = lease_path / "owner.json"
    oversized_evidence = b"{" + (b" " * (16 * 1024)) + b"}"
    owner_path.write_bytes(oversized_evidence)

    inspection = inspect_output_build_lease(destination)

    assert inspection.status == "invalid_owner_evidence"
    assert inspection.owner is None
    assert inspection.violations == ("owner_json_must_be_a_utf8_json_object",)
    assert owner_path.read_bytes() == oversized_evidence


def test_competing_acquisition_does_not_parse_or_mutate_oversized_owner_evidence(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    lease_path = tmp_path / ".artifact.akilan.lock"
    lease_path.mkdir()
    owner_path = lease_path / "owner.json"
    oversized_evidence = b"x" * ((16 * 1024) + 1)
    owner_path.write_bytes(oversized_evidence)

    with pytest.raises(OutputLeaseError, match="already leased"):
        OutputBuildLease(destination).acquire()

    assert owner_path.read_bytes() == oversized_evidence
    assert lease_path.is_dir()
