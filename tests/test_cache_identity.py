from __future__ import annotations

from pathlib import Path

import pytest

from akilan.cache_identity import build_artifact_cache_identity
from akilan.config import ExtractionConfig


def test_cache_identity_is_stable_and_excludes_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4\ncache identity fixture\n%%EOF\n")

    first = build_artifact_cache_identity(source, ExtractionConfig(overwrite=False))
    second = build_artifact_cache_identity(source, ExtractionConfig(overwrite=True))

    assert first == second
    assert len(first.key) == 64
    assert first.configuration["page_numbers"] is None
    assert "overwrite" not in first.configuration


def test_cache_identity_changes_for_semantic_inputs(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4\ncache identity fixture\n%%EOF\n")

    baseline = build_artifact_cache_identity(source)
    configured = build_artifact_cache_identity(source, ExtractionConfig(render_pages=True))
    schema = build_artifact_cache_identity(source, schema_version="1.1.0")
    package = build_artifact_cache_identity(source, package_version="99.0.0")

    assert len({baseline.key, configured.key, schema.key, package.key}) == 4


def test_cache_identity_changes_when_source_bytes_change(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"first")
    first = build_artifact_cache_identity(source)
    source.write_bytes(b"second")
    second = build_artifact_cache_identity(source)

    assert first.source_sha256 != second.source_sha256
    assert first.key != second.key


def test_cache_identity_normalizes_page_numbers_to_json_shape(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"fixture")

    identity = build_artifact_cache_identity(source, ExtractionConfig(page_numbers=(1, 3)))

    assert identity.configuration["page_numbers"] == [1, 3]
    assert identity.to_dict()["configuration"] == identity.configuration


@pytest.mark.parametrize("field", ["schema_version", "package_version"])
def test_cache_identity_rejects_blank_contract_versions(tmp_path: Path, field: str) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"fixture")

    kwargs = {field: "   "}
    with pytest.raises(ValueError, match=field):
        build_artifact_cache_identity(source, **kwargs)
