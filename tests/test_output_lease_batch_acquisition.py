from __future__ import annotations

import json
from pathlib import Path

import pytest

from akilan.output_lease import OutputBuildLease, OutputLeaseError, inspect_output_build_lease
from akilan.output_lease_batch import OutputBuildLeaseBatch


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
