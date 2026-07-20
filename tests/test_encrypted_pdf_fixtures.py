from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pymupdf
import pytest

from akilan import ExtractionConfig, PDFArtifactBuilder
from akilan.builder import PDFExtractionError

_SCRIPT = Path(__file__).parents[1] / "scripts" / "generate_encrypted_benchmark_fixtures.py"
_SPEC = importlib.util.spec_from_file_location("generate_encrypted_benchmark_fixtures", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_generate_encrypted_fixture_persists_expected_security_contract(tmp_path: Path) -> None:
    payload = _MODULE.generate_fixture(tmp_path / "corpus")

    assert payload["case_count"] == 1
    assert payload["credential_values_included"] is False
    assert payload["production_use_forbidden"] is True
    protected = payload["cases"][0]
    assert protected["case_id"] == "user_password"
    assert protected["is_pdf"] is True
    assert protected["is_encrypted"] is True
    assert protected["needs_password"] is True

    with pymupdf.open(protected["path"]) as document:
        assert document.needs_pass
        assert document.authenticate(_MODULE._USER_PASSWORD) > 0
        assert document.page_count == 1
        assert "AKILAN Benchmark: Encrypted User Password" in document[0].get_text()


def test_builder_rejects_missing_and_invalid_password_without_publishing_output(tmp_path: Path) -> None:
    protected = _MODULE.generate_fixture(tmp_path / "corpus")["cases"][0]
    destination = tmp_path / "artifact"
    builder = PDFArtifactBuilder(ExtractionConfig(overwrite=True))

    with pytest.raises(PDFExtractionError, match="missing or invalid"):
        builder.build(protected["path"], destination)
    assert not destination.exists()

    with pytest.raises(PDFExtractionError, match="missing or invalid"):
        builder.build(protected["path"], destination, password="wrong-password")
    assert not destination.exists()


def test_builder_authenticates_and_publishes_encrypted_artifact(tmp_path: Path) -> None:
    protected = _MODULE.generate_fixture(tmp_path / "corpus")["cases"][0]
    destination = tmp_path / "artifact"

    artifact = PDFArtifactBuilder(ExtractionConfig(overwrite=True)).build(
        protected["path"],
        destination,
        password=_MODULE._USER_PASSWORD,
    )

    assert artifact.document["needs_password"] is False
    assert artifact.document["page_count"] == 1
    assert artifact.statistics["text_block_count"] > 0
    assert (destination / "document.json").is_file()
    assert (destination / "manifest.json").is_file()


def test_main_writes_credential_free_machine_readable_evidence(tmp_path: Path, capsys: object) -> None:
    output = tmp_path / "corpus"
    evidence = tmp_path / "evidence" / "encrypted.json"

    exit_code = _MODULE.main([str(output), "--evidence", str(evidence)])

    assert exit_code == 0
    persisted = json.loads(evidence.read_text(encoding="utf-8"))
    assert persisted["case_count"] == 1
    assert persisted["cases"][0]["case_id"] == "user_password"
    assert persisted["cases"][0]["needs_password"] is True
    assert persisted["credential_values_included"] is False
    serialized = json.dumps(persisted)
    assert _MODULE._OWNER_PASSWORD not in serialized
    assert _MODULE._USER_PASSWORD not in serialized
    captured = capsys.readouterr()
    printed = json.loads(captured.out)
    assert printed["evidence"] == str(evidence.resolve())
