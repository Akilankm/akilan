from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from akilan.output_lease import (
    OutputBuildLease,
    OutputLeaseError,
    inspect_output_build_lease,
)

pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="Hard-link evidence semantics are validated on POSIX filesystems.",
)


def _replace_owner_with_hard_link(lease: OutputBuildLease, external: Path) -> bytes:
    owner_path = lease.path / "owner.json"
    payload = owner_path.read_bytes()
    external.write_bytes(payload)
    owner_path.unlink()
    os.link(external, owner_path)
    return payload


def test_inspection_rejects_hard_linked_owner_evidence_without_mutation(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination).acquire()
    external = tmp_path / "external-owner.json"
    payload = _replace_owner_with_hard_link(lease, external)

    inspection = inspect_output_build_lease(destination)

    assert inspection.status == "invalid_owner_evidence"
    assert inspection.owner is None
    assert inspection.violations == ("owner_json_must_have_single_link",)
    assert external.read_bytes() == payload
    assert (lease.path / "owner.json").read_bytes() == payload
    assert external.stat().st_nlink == 2

    (lease.path / "owner.json").unlink()
    lease.path.rmdir()
    assert external.read_bytes() == payload


def test_release_refuses_hard_linked_owner_evidence_and_preserves_external_inode(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination).acquire()
    external = tmp_path / "external-owner.json"
    payload = _replace_owner_with_hard_link(lease, external)

    with pytest.raises(OutputLeaseError, match="ownership changed"):
        lease.release()

    assert lease.path.is_dir()
    assert json.loads(external.read_text(encoding="utf-8")) == lease.owner.to_dict()
    assert external.read_bytes() == payload
    assert external.stat().st_nlink == 2

    (lease.path / "owner.json").unlink()
    lease.path.rmdir()
    assert external.read_bytes() == payload
