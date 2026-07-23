from __future__ import annotations

import json
from pathlib import Path

from akilan.output_lease import OutputBuildLease
from akilan.output_lease_batch_cli import main


def _write_manifest(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_batch_cli_accepts_exact_unleased_set_and_persists_equivalent_report(
    tmp_path: Path,
    capsys,
) -> None:
    manifest = tmp_path / "destinations.json"
    report = tmp_path / "reports" / "lease-preflight.json"
    _write_manifest(
        manifest,
        {
            "second": "outputs/b",
            "first": "outputs/a",
        },
    )

    exit_code = main([str(manifest), "--report", str(report)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    persisted = json.loads(report.read_text(encoding="utf-8"))
    assert output["ready"] is True
    assert output["status"] == "ready"
    assert output["destination_count"] == 2
    assert output["blocked_count"] == 0
    assert [entry["identifier"] for entry in output["entries"]] == ["first", "second"]
    assert output["report"] == str(report.resolve())
    assert persisted == {key: value for key, value in output.items() if key != "report"}


def test_batch_cli_rejects_complete_set_when_one_destination_is_leased(
    tmp_path: Path,
    capsys,
) -> None:
    leased = tmp_path / "outputs" / "leased"
    manifest = tmp_path / "destinations.json"
    _write_manifest(
        manifest,
        {
            "free": "outputs/free",
            "leased": "outputs/leased",
        },
    )

    with OutputBuildLease(leased):
        exit_code = main([str(manifest)])

    assert exit_code == 1
    output = json.loads(capsys.readouterr().err)
    assert output["ready"] is False
    assert output["status"] == "blocked"
    assert output["destination_count"] == 2
    assert output["blocked_count"] == 1
    assert [entry["inspection"]["status"] for entry in output["entries"]] == [
        "absent",
        "valid",
    ]


def test_batch_cli_rejects_malformed_or_non_object_manifests(
    tmp_path: Path,
    capsys,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not-json", encoding="utf-8")

    assert main([str(malformed)]) == 1
    malformed_output = json.loads(capsys.readouterr().err)
    assert malformed_output["status"] == "invalid_manifest_json"

    sequence = tmp_path / "sequence.json"
    _write_manifest(sequence, ["artifact"])

    assert main([str(sequence)]) == 1
    sequence_output = json.loads(capsys.readouterr().err)
    assert sequence_output["status"] == "invalid_manifest_root"


def test_batch_cli_rejects_empty_values_and_duplicate_resolved_destinations(
    tmp_path: Path,
    capsys,
) -> None:
    invalid = tmp_path / "invalid.json"
    _write_manifest(invalid, {"artifact": ""})

    assert main([str(invalid)]) == 1
    invalid_output = json.loads(capsys.readouterr().err)
    assert invalid_output["status"] == "invalid_destination"

    duplicate = tmp_path / "duplicate.json"
    _write_manifest(
        duplicate,
        {
            "first": "outputs/artifact",
            "second": "outputs/../outputs/artifact",
        },
    )

    assert main([str(duplicate)]) == 1
    duplicate_output = json.loads(capsys.readouterr().err)
    assert duplicate_output["status"] == "invalid_destination_set"
    assert duplicate_output["violations"] == ["duplicate_destination:first:second"]


def test_batch_cli_is_read_only_for_malformed_lease_evidence(
    tmp_path: Path,
    capsys,
) -> None:
    destination = tmp_path / "outputs" / "artifact"
    lease_path = destination.parent / ".artifact.akilan.lock"
    lease_path.mkdir(parents=True)
    owner_path = lease_path / "owner.json"
    owner_path.write_text("not-json", encoding="utf-8")
    manifest = tmp_path / "destinations.json"
    _write_manifest(manifest, {"artifact": "outputs/artifact"})

    assert main([str(manifest)]) == 1
    output = json.loads(capsys.readouterr().err)
    assert output["status"] == "blocked"
    assert output["entries"][0]["inspection"]["status"] == "invalid_owner_evidence"
    assert owner_path.read_text(encoding="utf-8") == "not-json"
