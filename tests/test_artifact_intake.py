from __future__ import annotations

from akilan.artifact_intake import assess_artifact_intake


def valid_artifact() -> dict[str, object]:
    bbox = {"x0": 0.0, "y0": 0.0, "x1": 100.0, "y1": 200.0}
    return {
        "schema_version": "1.0.0",
        "generator": {},
        "source": {},
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
                "reading_order": [],
                "metrics": {},
            }
        ],
        "statistics": {},
        "artifact_files": {},
    }


def test_valid_artifact_is_accepted() -> None:
    report = assess_artifact_intake(valid_artifact())

    assert report.accepted is True
    assert report.violations == ()
    assert report.to_dict()["compatibility"]["status"] == "compatible"


def test_malformed_schema_version_fails_closed_even_when_structure_is_valid() -> None:
    artifact = valid_artifact()
    artifact["schema_version"] = "1"

    report = assess_artifact_intake(artifact)

    assert report.accepted is False
    assert report.compatibility.status.value == "invalid"
    assert report.to_dict()["violation_count"] == 0


def test_unsupported_major_and_structural_errors_are_reported_together() -> None:
    artifact = valid_artifact()
    artifact["schema_version"] = "2.0.0"
    artifact["pages"][0]["width"] = 0  # type: ignore[index]

    report = assess_artifact_intake(artifact)
    payload = report.to_dict()

    assert report.accepted is False
    assert payload["compatibility"]["status"] == "unsupported_major"
    assert payload["violation_count"] == 2
    assert payload["violations"][0]["path"] == "$.schema_version"
    assert payload["violations"][1] == {
        "path": "$.pages[0].width",
        "message": "must be a positive number",
    }


def test_artifact_is_not_mutated() -> None:
    artifact = valid_artifact()
    before = repr(artifact)

    assess_artifact_intake(artifact)

    assert repr(artifact) == before
