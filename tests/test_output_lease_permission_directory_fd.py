from __future__ import annotations

import pathlib
import os

import pytest

from akilan.output_lease import OutputBuildLease
from akilan.output_lease_security import inspect_output_build_lease_permissions


pytestmark = pytest.mark.skipif(
    not (
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and os.open in os.supports_dir_fd
    ),
    reason="requires descriptor-relative POSIX filesystem semantics",
)


def test_permission_audit_stays_anchored_when_lease_path_is_replaced(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination).acquire()
    displaced = tmp_path / "displaced-lease"
    external = tmp_path / "external-lease"
    external.mkdir(mode=0o700)
    external_owner = external / "owner.json"
    external_owner.write_text("{}", encoding="utf-8")
    external_owner.chmod(0o666)

    original_open = os.open
    replaced = False

    def replace_before_owner_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal replaced
        if path == "owner.json" and dir_fd is not None and not replaced:
            lease.path.rename(displaced)
            lease.path.symlink_to(external, target_is_directory=True)
            replaced = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr("akilan.output_lease_security.os.open", replace_before_owner_open)

    inspection = inspect_output_build_lease_permissions(destination)

    assert replaced
    assert inspection.status == "secure"
    assert inspection.secure
    assert inspection.lease_mode == "0700"
    assert inspection.owner_mode == "0600"
    assert external_owner.stat().st_mode & 0o002

    lease.path.unlink()
    displaced.rename(lease.path)
    lease.release()
