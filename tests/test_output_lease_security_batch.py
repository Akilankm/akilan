from __future__ import annotations

import os
from pathlib import Path

import pytest

from akilan.output_lease import OutputBuildLease
from akilan.output_lease_security_batch import inspect_output_lease_permission_batch


def test_batch_permission_audit_rejects_empty_destination_set() -> None:
    inspection = inspect_output_lease_permission_batch({})

    assert inspection.status == "invalid_destination_set"
    assert not inspection.secure
    assert inspection.destination_count == 0
    assert inspection.insecure_count == 0
    assert inspection.violations == ("destination_set_must_not_be_empty",)


def test_batch_permission_audit_is_deterministic_for_absent_leases(
    tmp_path: Path,
) -> None:
    inspection = inspect_output_lease_permission_batch(
        {
            "second": tmp_path / "second",
            "first": tmp_path / "first",
        }
    )

    assert inspection.status == "secure"
    assert inspection.secure
    assert inspection.destination_count == 2
    assert inspection.insecure_count == 0
    assert tuple(entry.identifier for entry in inspection.entries) == ("first", "second")
    assert all(entry.inspection.status == "absent" for entry in inspection.entries)
    assert inspection.to_dict() == inspect_output_lease_permission_batch(
        {
            "first": tmp_path / "first",
            "second": tmp_path / "second",
        }
    ).to_dict()


def test_batch_permission_audit_rejects_duplicate_resolved_destinations(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "artifact"

    inspection = inspect_output_lease_permission_batch(
        {"primary": destination, "alias": destination / ".." / "artifact"}
    )

    assert inspection.status == "invalid_destination_set"
    assert not inspection.secure
    assert inspection.violations == ("duplicate_destination:alias:primary",)


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits are required")
def test_batch_permission_audit_fails_complete_set_closed_without_mutation(
    tmp_path: Path,
) -> None:
    secure_destination = tmp_path / "secure"
    insecure_destination = tmp_path / "insecure"

    with (
        OutputBuildLease(secure_destination) as secure_lease,
        OutputBuildLease(insecure_destination) as insecure_lease,
    ):
        owner_path = insecure_lease.path / "owner.json"
        owner_path.chmod(owner_path.stat().st_mode | 0o020)

        inspection = inspect_output_lease_permission_batch(
            {
                "secure": secure_destination,
                "insecure": insecure_destination,
            }
        )

        assert inspection.status == "insecure"
        assert not inspection.secure
        assert inspection.destination_count == 2
        assert inspection.insecure_count == 1
        assert inspection.violations == (
            "destination_permission_audit_failed:insecure",
        )
        assert secure_lease.path.is_dir()
        assert insecure_lease.path.is_dir()
        assert owner_path.is_file()
        by_identifier = {entry.identifier: entry.inspection for entry in inspection.entries}
        assert by_identifier["secure"].secure
        assert not by_identifier["insecure"].secure
