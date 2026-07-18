from __future__ import annotations

from akilan import load_artifact_json_schema
from akilan.schema import SUPPORTED_SCHEMA_MAJOR


def test_packaged_schema_declares_supported_major_contract() -> None:
    schema = load_artifact_json_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"
    assert schema["properties"]["schema_version"]["pattern"].startswith(f"^{SUPPORTED_SCHEMA_MAJOR}")


def test_packaged_schema_matches_dependency_free_validator_requirements() -> None:
    schema = load_artifact_json_schema()

    assert schema["required"] == [
        "schema_version",
        "generator",
        "source",
        "document",
        "table_of_contents",
        "embedded_files",
        "pages",
        "statistics",
        "artifact_files",
    ]

    page_schema = schema["$defs"]["page"]
    assert page_schema["additionalProperties"] is True
    assert set(page_schema["required"]) >= {
        "page_index",
        "page_number",
        "label",
        "width",
        "height",
        "rotation",
        "mediabox",
        "cropbox",
        "reading_order",
        "metrics",
    }


def test_schema_loader_returns_independent_objects() -> None:
    first = load_artifact_json_schema()
    second = load_artifact_json_schema()

    first["title"] = "mutated"

    assert second["title"] == "AKILAN Document Artifact v1"
