from __future__ import annotations

from pathlib import Path

import pytest

from akilan import output_lease
from akilan.output_lease import OutputBuildLease, inspect_output_build_lease


@pytest.mark.parametrize("interrupt_type", [KeyboardInterrupt, SystemExit])
def test_output_lease_acquisition_rolls_back_process_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupt_type: type[BaseException],
) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination)

    def interrupt_owner_write(*_args: object, **_kwargs: object) -> None:
        raise interrupt_type("expected interruption")

    monkeypatch.setattr(output_lease, "_write_owner", interrupt_owner_write)

    with pytest.raises(interrupt_type, match="expected interruption"):
        lease.acquire()

    assert not lease.path.exists()
    assert inspect_output_build_lease(destination).status == "absent"


def test_output_lease_can_be_acquired_after_interrupted_owner_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "artifact"
    interrupted = OutputBuildLease(destination)
    original_write_owner = output_lease._write_owner

    def interrupt_owner_write(*_args: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt("expected interruption")

    monkeypatch.setattr(output_lease, "_write_owner", interrupt_owner_write)
    with pytest.raises(KeyboardInterrupt, match="expected interruption"):
        interrupted.acquire()

    monkeypatch.setattr(output_lease, "_write_owner", original_write_owner)
    with OutputBuildLease(destination) as recovered:
        assert recovered.path.is_dir()
        assert inspect_output_build_lease(destination).status == "valid"

    assert inspect_output_build_lease(destination).status == "absent"
