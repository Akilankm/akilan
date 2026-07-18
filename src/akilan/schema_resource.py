"""Packaged machine-readable artifact schema access."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

_SCHEMA_PACKAGE = "akilan.schemas"
_SCHEMA_NAME = "document-artifact-v1.schema.json"


def load_artifact_json_schema() -> dict[str, Any]:
    """Return a fresh JSON-decoded copy of the canonical v1 artifact schema.

    The schema is packaged with AKILAN so downstream systems and CI jobs can
    inspect the contract without network access or an additional dependency.
    Validation remains available through :func:`akilan.validate_artifact`.
    """

    schema_path = files(_SCHEMA_PACKAGE).joinpath(_SCHEMA_NAME)
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    if not isinstance(schema, dict):
        raise RuntimeError(f"Packaged artifact schema is not a JSON object: {_SCHEMA_NAME}")
    return schema
