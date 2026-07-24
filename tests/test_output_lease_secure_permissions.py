from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from akilan.output_lease import OutputBuildLease, inspect_output_build_lease
from akilan.output_lease_security import inspect_output_build_lease_permissions


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode-bit contract")
def test_acquisition_enforces_private_modes_under_permissive_umask(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    previous_umask = os.umask(0)
    try:
        lease = OutputBuildLease(destination).acquire()
    finally:
        os.umask(previous_umask)

    try:
        lease_mode = stat.S_IMODE(lease.path.stat().st_mode)
        owner_mode = stat.S_IMODE((lease.path / "owner.json").stat().st_mode)

        assert lease_mode == 0o700
        assert owner_mode == 0o600
        permission_evidence = inspect_output_build_lease_permissions(destination)
        assert permission_evidence.secure
        assert permission_evidence.violations == ()
    finally:
        lease.release()


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode-bit contract")
def test_directory_mode_failure_rolls_back_without_stranding_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination)

    def fail_mode(path: Path, mode: int) -> None:
        assert path == lease.path
        assert mode == 0o700
        raise OSError("simulated permission hardening failure")

    monkeypatch.setattr("akilan.output_lease._set_posix_mode", fail_mode)

    with pytest.raises(OSError, match="simulated permission hardening failure"):
        lease.acquire()

    assert not lease.path.exists()
    assert inspect_output_build_lease(destination).status == "absent"


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode-bit contract")
def test_owner_staging_file_is_private_before_atomic_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination)
    observed_modes: list[int] = []
    original_replace = os.replace

    def inspect_then_replace(source: str | bytes | Path, target: str | bytes | Path) -> None:
        observed_modes.append(stat.S_IMODE(Path(source).stat().st_mode))
        original_replace(source, target)

    monkeypatch.setattr("akilan.output_lease.os.replace", inspect_then_replace)

    lease.acquire()
    try:
        assert observed_modes == [0o600]
    finally:
        lease.release()
