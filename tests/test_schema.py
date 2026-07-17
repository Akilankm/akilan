from __future__ import annotations

import pytest

from akilan.schema import ArtifactSchemaError, validate_artifact


def valid_artifact() -> dict[str, object]:
    bbox = {"x0": 0.0, "y0": 0.0, "x1": 100.0, "y1": 200.0, "width": 100.0, "height": 200.0}
    return {
        "schema_version": "1.0.0",
        "generator": {"name": "akilan", "version": "0.1.0"},
        "source": {"path": "data/example.pdf"},
        "document": {},
        "table_of_contents": [],
        "embedded_files": [],
        "pages": [
            {
                "page_index": 0,
                "page_number": 1,
                "label": "1",
                "width": 100.0,
                "height": 200.0,
                "rotation": 0,
                "mediabox": bbox,
                "cropbox": bbox,
                "text_blocks": [],
                "tables": [],
                "images": [],
                "drawings": [],
                "links": [],
                "annotations": [],
                "widgets": [],
                "reading_order": [
                    {
                        "order": 0,
                        "element_type": "text",
                        "element_id": "p0001-text-0001",
                        "bbox": [0.0, 0.0, 10.0, 10.0],
                        "column_index": 0,
                    }
                ],
                "markdown_path": None,
                "json_path": None,
                "render_path": None,
                "metrics": {},
            }
        ],
        "statistics": {},
        "artifact_files": {},
    }


def test_valid_artifact_has_no_violations() -> None:
    assert validate_artifact(valid_artifact()) == []


def test_validator_collects_actionable_paths() -> None:
    artifact = valid_artifact()
    artifact["schema_version"] = "2.0.0"
    page = artifact["pages"][0]  # type: ignore[index]
    page["width"] = 0  # type: ignore[index]
    page["reading_order"].append(dict(page["reading_order"][0]))  # type: ignore[index]

    violations = validate_artifact(artifact, raise_on_error=False)
    rendered = {str(violation) for violation in violations}

    assert any("$.schema_version: unsupported major version 2" in item for item in rendered)
    assert "$.pages[0].width: must be a positive number" in rendered
    assert "$.pages[0].reading_order[1].order: duplicates reading order 0" in rendered


def test_validator_raises_one_error_with_all_violations() -> None:
    artifact = valid_artifact()
    del artifact["statistics"]
    page = artifact["pages"][0]  # type: ignore[index]
    page["cropbox"] = {"x0": 10.0, "y0": 0.0, "x1": 1.0, "y1": 20.0}  # type: ignore[index]

    with pytest.raises(ArtifactSchemaError) as error:
        validate_artifact(artifact)

    assert len(error.value.violations) == 2
    assert "$.statistics: is required" in str(error.value)
    assert "$.pages[0].cropbox: must satisfy x1 >= x0" in str(error.value)
