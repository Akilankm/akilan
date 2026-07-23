from __future__ import annotations

import json
from pathlib import Path

import pytest

from akilan.output_lease import OutputBuildLease, OutputLeaseError, inspect_output_build_lease
from akilan.output_lease_batch import (
    OutputBuildLeaseBatch,
    OutputLeaseBatchContextError,
)


def test_batch_acquires_and_releases_exact_destination_set(tmp_path: Path) -> None:
    destinations = {
        "second": tmp_path / "artifact-b",
        "first": tmp_path / "artifact-a",
    }
    batch = OutputBuildLeaseBatch(destinations)

    assert batch.identifiers == ("first", "second")
    assert not batch.acquired

    with batch:
        assert batch.acquired
        assert set(batch.leases) == {"first", "second"}
        assert all(
            inspect_output_build_lease(destination).status == "valid"
            for destination in destinations.values()
        )

    assert not batch.acquired
    assert all(
        inspect_output_build_lease(destination).status == "absent"
        for destination in destinations.values()
    )


def test_batch_rolls_back_earlier_leases_when_later_acquisition_loses_race(
    tmp_path: Path,
) -> None:
    first = tmp_path / "artifact-a"
    second = tmp_path / "artifact-b"
    batch = OutputBuildLeaseBatch({"first": first, "second": second})

    with OutputBuildLease(second):
        with pytest.raises(OutputLeaseError, match="already leased"):
            batch.acquire()

        assert not batch.acquired
        assert inspect_output_build_lease(first).status == "absent"
        assert inspect_output_build_lease(second).status == "valid"

    assert inspect_output_build_lease(second).status == "absent"


@pytest.mark.parametrize(
    "interrupt",
    [KeyboardInterrupt("operator interrupt"), SystemExit(130)],
    ids=["keyboard-interrupt", "system-exit"],
)
def test_batch_rolls_back_partial_acquisition_for_process_interrupts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupt: BaseException,
) -> None:
    destinations = {
        "first": tmp_path / "artifact-a",
        "second": tmp_path / "artifact-b",
    }
    batch = OutputBuildLeaseBatch(destinations)
    second_lease = batch.leases["second"]
    original_acquire = OutputBuildLease.acquire

    def interrupt_second(lease: OutputBuildLease) -> OutputBuildLease:
        if lease is second_lease:
            raise interrupt
        return original_acquire(lease)

    monkeypatch.setattr(OutputBuildLease, "acquire", interrupt_second)

    with pytest.raises(type(interrupt)) as raised:
        batch.acquire()

    assert raised.value is interrupt
    assert not batch.acquired
    assert all(
        inspect_output_build_lease(destination).status == "absent"
        for destination in destinations.values()
    )


def test_batch_rejects_invalid_destination_set_without_side_effects(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with pytest.raises(OutputLeaseError, match="invalid_destination_set"):
        OutputBuildLeaseBatch(
            {
                "first": destination,
                "second": destination / ".." / "artifact",
            }
        )

    assert inspect_output_build_lease(destination).status == "absent"


def test_batch_release_fails_closed_when_owner_evidence_changes(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    batch = OutputBuildLeaseBatch({"artifact": destination}).acquire()
    owner_path = batch.leases["artifact"].path / "owner.json"
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["hostname"] = "changed-host"
    owner_path.write_text(json.dumps(owner, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(OutputLeaseError, match="release was incomplete"):
        batch.release()

    assert owner_path.exists()
    assert inspect_output_build_lease(destination).status == "valid"


def test_batch_release_continues_after_one_destination_ownership_changes(tmp_path: Path) -> None:
    destinations = {
        "first": tmp_path / "artifact-a",
        "second": tmp_path / "artifact-b",
        "third": tmp_path / "artifact-c",
    }
    batch = OutputBuildLeaseBatch(destinations).acquire()
    changed_owner_path = batch.leases["second"].path / "owner.json"
    changed_owner = json.loads(changed_owner_path.read_text(encoding="utf-8"))
    changed_owner["hostname"] = "changed-host"
    changed_owner_path.write_text(
        json.dumps(changed_owner, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(OutputLeaseError, match="second:OutputLeaseError"):
        batch.release()

    assert not batch.acquired
    assert inspect_output_build_lease(destinations["first"]).status == "absent"
    assert inspect_output_build_lease(destinations["second"]).status == "valid"
    assert inspect_output_build_lease(destinations["third"]).status == "absent"

    changed_owner_path.write_text(
        json.dumps(batch.leases["second"].owner.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    batch.release()

    assert inspect_output_build_lease(destinations["second"]).status == "absent"


def test_context_manager_preserves_body_and_cleanup_failures(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    batch = OutputBuildLeaseBatch({"artifact": destination})

    with pytest.raises(OutputLeaseBatchContextError) as raised, batch:
        owner_path = batch.leases["artifact"].path / "owner.json"
        owner = json.loads(owner_path.read_text(encoding="utf-8"))
        owner["hostname"] = "changed-host"
        owner_path.write_text(
            json.dumps(owner, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise RuntimeError("build failed")

    error = raised.value
    assert isinstance(error.body_error, RuntimeError)
    assert str(error.body_error) == "build failed"
    assert isinstance(error.release_error, OutputLeaseError)
    assert "release was incomplete" in str(error.release_error)
    assert error.__cause__ is error.body_error
    assert inspect_output_build_lease(destination).status == "valid"


def test_context_manager_keeps_cleanup_failure_behavior_without_body_error(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "artifact"
    batch = OutputBuildLeaseBatch({"artifact": destination})

    with pytest.raises(OutputLeaseError, match="release was incomplete") as raised, batch:
        owner_path = batch.leases["artifact"].path / "owner.json"
        owner = json.loads(owner_path.read_text(encoding="utf-8"))
        owner["hostname"] = "changed-host"
        owner_path.write_text(
            json.dumps(owner, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    assert not isinstance(raised.value, OutputLeaseBatchContextError)
    assert inspect_output_build_lease(destination).status == "valid"
