from __future__ import annotations

import os
from pathlib import Path

import pytest

from akilan.output_lease import OutputBuildLease
from akilan.output_lease_security import inspect_output_build_lease_permissions


def test_permission_inspection_reports_absent_lease(tmp_path: Path) -> None:
    inspection = inspect_output_build_lease_permissions(tmp_path / "artifact")

    assert inspection.status == "absent"
    assert inspection.secure
    assert inspection.lease_mode is None
    assert inspection.owner_mode is None
    assert inspection.violations == ()


def test_permission_inspection_fails_closed_when_platform_is_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "artifact"

    with OutputBuildLease(destination):
        monkeypatch.setattr(
            "akilan.output_lease_security._supports_posix_permission_audit",
            lambda: False,
        )
        inspection = inspect_output_build_lease_permissions(destination)

        assert inspection.status == "unsupported"
        assert not inspection.secure
        assert inspection.lease_mode is None
        assert inspection.owner_mode is None
        assert inspection.violations == ("posix_permission_audit_is_unsupported",)


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits are required")
def test_permission_inspection_reports_secure_lease_without_mutation(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with OutputBuildLease(destination) as lease:
        inspection = inspect_output_build_lease_permissions(destination)

        assert inspection.status == "secure"
        assert inspection.secure
        assert inspection.lease_mode is not None
        assert inspection.owner_mode is not None
        assert inspection.violations == ()
        assert lease.path.is_dir()
        assert (lease.path / "owner.json").is_file()


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits are required")
def test_permission_inspection_rejects_group_writable_owner_evidence(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with OutputBuildLease(destination) as lease:
        owner_path = lease.path / "owner.json"
        owner_path.chmod(owner_path.stat().st_mode | 0o020)

        inspection = inspect_output_build_lease_permissions(destination)

        assert inspection.status == "insecure_permissions"
        assert not inspection.secure
        assert inspection.violations == (
            "owner_json_must_not_be_group_or_world_writable",
        )
        assert inspection.owner_mode is not None
        assert int(inspection.owner_mode, 8) & 0o020
        assert owner_path.is_file()


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits are required")
def test_permission_inspection_reports_all_writable_boundary_violations(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with OutputBuildLease(destination) as lease:
        owner_path = lease.path / "owner.json"
        lease.path.chmod(lease.path.stat().st_mode | 0o002)
        owner_path.chmod(owner_path.stat().st_mode | 0o002)

        inspection = inspect_output_build_lease_permissions(destination)

        assert inspection.status == "insecure_permissions"
        assert not inspection.secure
        assert inspection.violations == (
            "lease_directory_must_not_be_group_or_world_writable",
            "owner_json_must_not_be_group_or_world_writable",
        )
        assert lease.path.is_dir()
        assert owner_path.is_file()
