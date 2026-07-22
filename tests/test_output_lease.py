from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from akilan import ExtractionConfig, PDFArtifactBuilder
from akilan.output_lease import OutputBuildLease, OutputLeaseError


def _make_pdf(path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "lease test")
    document.save(path)
    document.close()


def test_output_lease_rejects_competing_owner_and_preserves_evidence(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"

    with OutputBuildLease(destination) as first:
        owner_path = first.path / "owner.json"
        owner = json.loads(owner_path.read_text(encoding="utf-8"))

        assert owner["token"] == first.owner.token
        assert owner["destination"] == str(destination.resolve())
        with pytest.raises(OutputLeaseError, match="already leased"):
            OutputBuildLease(destination).acquire()
        assert json.loads(owner_path.read_text(encoding="utf-8")) == owner

    assert not first.path.exists()


def test_output_lease_is_released_when_build_scope_fails(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination)

    with pytest.raises(RuntimeError, match="expected failure"), lease:
        raise RuntimeError("expected failure")

    assert not lease.path.exists()


def test_output_lease_refuses_to_remove_changed_ownership(tmp_path: Path) -> None:
    destination = tmp_path / "artifact"
    lease = OutputBuildLease(destination).acquire()
    owner_path = lease.path / "owner.json"
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["token"] = "replacement-owner"
    owner_path.write_text(json.dumps(owner), encoding="utf-8")

    with pytest.raises(OutputLeaseError, match="ownership changed"):
        lease.release()

    assert lease.path.is_dir()
    owner_path.unlink()
    lease.path.rmdir()


def test_builder_fails_before_staging_when_destination_is_leased(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    destination = tmp_path / "artifact"
    _make_pdf(pdf)

    with OutputBuildLease(destination), pytest.raises(OutputLeaseError, match="already leased"):
        PDFArtifactBuilder(ExtractionConfig(overwrite=True)).build(pdf, destination)

    assert not destination.exists()
    assert not list(tmp_path.glob(".artifact.akilan-*.tmp"))
    assert not list(tmp_path.glob(".artifact.akilan-*.bak"))
