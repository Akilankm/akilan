from __future__ import annotations

import pytest

from akilan.manifest_schema import validate_manifest
from akilan.schema import ArtifactSchemaError


def valid_manifest() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "generator": {"name": "akilan"},
        "source": {"file_name": "example.pdf"},
        "document": {"page_count": 1},
        "statistics": {},
        "artifact_files": {
            "manifest": "manifest.json",
            "document_json": "document.json",
            "pages": ["pages/page_0001.json"],
            "page_markdown": [],
            "images": [],
            "renders": [],
        },
        "pages": [
            {
                "page_number": 1,
                "label": "1",
                "json_path": "pages/page_0001.json",
                "markdown_path": None,
                "render_path": None,
                "metrics": {},
            }
        ],
    }


def test_valid_manifest_has_no_violations() -> None:
    assert validate_manifest(valid_manifest()) == []


def test_manifest_validator_collects_actionable_violations() -> None:
    manifest = valid_manifest()
    manifest["schema_version"] = ""
    manifest["artifact_files"] = {"manifest": "", "document_json": None, "pages": [""]}
    manifest["pages"] = [
        {"page_number": 1, "json_path": "pages/page_0001.json", "metrics": {}},
        {"page_number": 1, "json_path": "", "metrics": []},
    ]

    violations = validate_manifest(manifest, raise_on_error=False)
    rendered = {str(item) for item in violations}

    assert "$.schema_version: must be a non-empty string" in rendered
    assert "$.artifact_files.manifest: must be a non-empty string" in rendered
    assert "$.artifact_files.document_json: must be a non-empty string" in rendered
    assert "$.artifact_files.pages[0]: must be a non-empty string" in rendered
    assert "$.pages[1].page_number: duplicates page number 1" in rendered
    assert "$.pages[1].json_path: must be null or a non-empty string" in rendered
    assert "$.pages[1].metrics: must be an object" in rendered


def test_manifest_validator_raises_aggregated_error() -> None:
    with pytest.raises(ArtifactSchemaError) as error:
        validate_manifest({})

    assert len(error.value.violations) == 7
    assert "$.pages: is required" in str(error.value)


def test_manifest_validator_rejects_non_object() -> None:
    violations = validate_manifest([], raise_on_error=False)  # type: ignore[arg-type]
    assert [str(item) for item in violations] == ["$: must be an object"]
