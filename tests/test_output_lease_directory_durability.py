from __future__ import annotations

from pathlib import Path

import pytest

from akilan import output_lease
from akilan.output_lease import OutputBuildLease, inspect_output_build_lease


def test_output_lease_synchronizes_owner_directory_after_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "artifact"
    synchronized: list[Path] = []

    monkeypatch.setattr(
        output_lease,
        "_sync_directory",
        lambda path: synchronized.append(path),
    )

    with OutputBuildLease(destination) as lease:
        assert synchronized == [lease.path]
        assert (lease.path / "owner.json").is_file()


def test_output_lease_rolls_back_when_directory_sync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination)
    synchronized: list[Path] = []

    def fail_publication_directory_sync(path: Path) -> None:
        synchronized.append(path)
        if path == lease.path:
            assert (path / "owner.json").is_file()
            raise OSError("simulated directory durability failure")
        assert path == lease.path.parent

    monkeypatch.setattr(
        output_lease,
        "_sync_directory",
        fail_publication_directory_sync,
    )

    with pytest.raises(OSError, match="simulated directory durability failure"):
        lease.acquire()

    assert synchronized == [lease.path, lease.path.parent]
    assert not lease.path.exists()
    assert inspect_output_build_lease(destination).status == "absent"
