from __future__ import annotations

from pathlib import Path

from akilan.output_lease import OutputBuildLease
from akilan.output_lease_batch import assess_output_lease_batch_preflight


def test_batch_preflight_is_ready_for_exact_unleased_destination_set(tmp_path: Path) -> None:
    report = assess_output_lease_batch_preflight(
        {
            "second": tmp_path / "artifact-b",
            "first": tmp_path / "artifact-a",
        }
    )

    assert report.ready
    assert report.status == "ready"
    assert report.destination_count == 2
    assert report.blocked_count == 0
    assert [entry.identifier for entry in report.entries] == ["first", "second"]
    assert all(entry.inspection.status == "absent" for entry in report.entries)


def test_batch_preflight_blocks_complete_set_when_one_destination_is_leased(tmp_path: Path) -> None:
    leased_destination = tmp_path / "artifact-b"

    with OutputBuildLease(leased_destination) as lease:
        report = assess_output_lease_batch_preflight(
            {
                "first": tmp_path / "artifact-a",
                "second": leased_destination,
            }
        )

        assert not report.ready
        assert report.status == "blocked"
        assert report.destination_count == 2
        assert report.blocked_count == 1
        assert report.entries[0].inspection.status == "absent"
        assert report.entries[1].inspection.status == "valid"
        assert lease.path.is_dir()


def test_batch_preflight_blocks_malformed_lease_without_mutation(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    lease_path = tmp_path / ".artifact.akilan.lock"
    lease_path.mkdir()
    owner_path = lease_path / "owner.json"
    owner_path.write_text("not-json", encoding="utf-8")

    report = assess_output_lease_batch_preflight({"artifact": destination})

    assert not report.ready
    assert report.status == "blocked"
    assert report.blocked_count == 1
    assert report.entries[0].inspection.status == "invalid_owner_evidence"
    assert owner_path.read_text(encoding="utf-8") == "not-json"


def test_batch_preflight_rejects_empty_and_duplicate_destination_sets(tmp_path: Path) -> None:
    empty = assess_output_lease_batch_preflight({})
    assert empty.status == "invalid_destination_set"
    assert empty.violations == ("destination_set_must_not_be_empty",)

    destination = tmp_path / "artifact"
    duplicate = assess_output_lease_batch_preflight(
        {
            "first": destination,
            "second": destination / ".." / "artifact",
        }
    )
    assert not duplicate.ready
    assert duplicate.status == "invalid_destination_set"
    assert duplicate.violations == ("duplicate_destination:first:second",)


def test_batch_preflight_serialization_is_deterministic(tmp_path: Path) -> None:
    first = assess_output_lease_batch_preflight(
        {
            "zeta": tmp_path / "zeta",
            "alpha": tmp_path / "alpha",
        }
    ).to_dict()
    second = assess_output_lease_batch_preflight(
        {
            "alpha": tmp_path / "alpha",
            "zeta": tmp_path / "zeta",
        }
    ).to_dict()

    assert first == second
    assert [entry["identifier"] for entry in first["entries"]] == ["alpha", "zeta"]
