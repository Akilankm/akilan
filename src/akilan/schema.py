"""Dependency-free validation for canonical AKILAN artifacts.

The validator intentionally checks the stable public contract rather than every
implementation detail. It is suitable for CI gates, persisted-artifact intake,
and downstream compatibility checks without adding a runtime dependency.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SUPPORTED_SCHEMA_MAJOR = 1


@dataclass(frozen=True, slots=True)
class SchemaViolation:
    """One actionable artifact contract violation."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class ArtifactSchemaError(ValueError):
    """Raised when an artifact does not satisfy the canonical contract."""

    def __init__(self, violations: Sequence[SchemaViolation]) -> None:
        self.violations = tuple(violations)
        details = "\n".join(f"- {violation}" for violation in self.violations)
        super().__init__(f"Artifact schema validation failed with {len(self.violations)} violation(s):\n{details}")


def validate_artifact(artifact: Mapping[str, Any], *, raise_on_error: bool = True) -> list[SchemaViolation]:
    """Validate a JSON-decoded AKILAN document artifact.

    Returns all detected violations so callers can present a complete repair
    report. By default, :class:`ArtifactSchemaError` is raised when any
    violation exists.
    """

    violations: list[SchemaViolation] = []
    _require_mapping(artifact, "$", violations)
    if violations:
        return _finish(violations, raise_on_error)

    schema_version = _required(artifact, "schema_version", "$", violations)
    if schema_version is not None:
        _validate_schema_version(schema_version, "$.schema_version", violations)

    for key in ("generator", "source", "document", "statistics", "artifact_files"):
        value = _required(artifact, key, "$", violations)
        if value is not None:
            _require_mapping(value, f"$.{key}", violations)

    for key in ("table_of_contents", "embedded_files", "pages"):
        value = _required(artifact, key, "$", violations)
        if value is not None:
            _require_sequence(value, f"$.{key}", violations)

    pages = artifact.get("pages")
    if _is_sequence(pages):
        for index, page in enumerate(pages):
            _validate_page(page, f"$.pages[{index}]", violations)

    return _finish(violations, raise_on_error)


def _validate_schema_version(value: Any, path: str, violations: list[SchemaViolation]) -> None:
    if not isinstance(value, str) or not value.strip():
        violations.append(SchemaViolation(path, "must be a non-empty string"))
        return
    major_text = value.split(".", maxsplit=1)[0]
    try:
        major = int(major_text)
    except ValueError:
        violations.append(SchemaViolation(path, "must begin with an integer major version"))
        return
    if major != SUPPORTED_SCHEMA_MAJOR:
        violations.append(
            SchemaViolation(path, f"unsupported major version {major}; expected {SUPPORTED_SCHEMA_MAJOR}.x")
        )


def _validate_page(value: Any, path: str, violations: list[SchemaViolation]) -> None:
    if not _require_mapping(value, path, violations):
        return

    for key in ("page_index", "page_number", "rotation"):
        item = _required(value, key, path, violations)
        if item is not None and (not isinstance(item, int) or isinstance(item, bool)):
            violations.append(SchemaViolation(f"{path}.{key}", "must be an integer"))

    for key in ("width", "height"):
        item = _required(value, key, path, violations)
        if item is not None and (not isinstance(item, (int, float)) or isinstance(item, bool) or item <= 0):
            violations.append(SchemaViolation(f"{path}.{key}", "must be a positive number"))

    label = _required(value, "label", path, violations)
    if label is not None and not isinstance(label, str):
        violations.append(SchemaViolation(f"{path}.label", "must be a string"))

    for key in ("mediabox", "cropbox"):
        bbox = _required(value, key, path, violations)
        if bbox is not None:
            _validate_bbox(bbox, f"{path}.{key}", violations)

    for key in (
        "text_blocks",
        "tables",
        "images",
        "drawings",
        "links",
        "annotations",
        "widgets",
        "reading_order",
    ):
        items = _required(value, key, path, violations)
        if items is not None:
            _require_sequence(items, f"{path}.{key}", violations)

    metrics = _required(value, "metrics", path, violations)
    if metrics is not None:
        _require_mapping(metrics, f"{path}.metrics", violations)

    _validate_reading_order(value, path, violations)


def _validate_reading_order(page: Mapping[str, Any], path: str, violations: list[SchemaViolation]) -> None:
    items = page.get("reading_order")
    if not _is_sequence(items):
        return

    observed_orders: set[int] = set()
    for index, item in enumerate(items):
        item_path = f"{path}.reading_order[{index}]"
        if not _require_mapping(item, item_path, violations):
            continue
        order = _required(item, "order", item_path, violations)
        if order is not None:
            if not isinstance(order, int) or isinstance(order, bool) or order < 0:
                violations.append(SchemaViolation(f"{item_path}.order", "must be a non-negative integer"))
            elif order in observed_orders:
                violations.append(SchemaViolation(f"{item_path}.order", f"duplicates reading order {order}"))
            else:
                observed_orders.add(order)
        element_type = _required(item, "element_type", item_path, violations)
        if element_type is not None and element_type not in {"text", "table", "image", "drawing"}:
            violations.append(SchemaViolation(f"{item_path}.element_type", "must be text, table, image, or drawing"))
        element_id = _required(item, "element_id", item_path, violations)
        if element_id is not None and (not isinstance(element_id, str) or not element_id):
            violations.append(SchemaViolation(f"{item_path}.element_id", "must be a non-empty string"))
        bbox = _required(item, "bbox", item_path, violations)
        if bbox is not None:
            _validate_bbox(bbox, f"{item_path}.bbox", violations)


def _validate_bbox(value: Any, path: str, violations: list[SchemaViolation]) -> None:
    coordinates: list[Any]
    if isinstance(value, Mapping):
        required = ("x0", "y0", "x1", "y1")
        missing = [key for key in required if key not in value]
        if missing:
            violations.append(SchemaViolation(path, f"is missing coordinate(s): {', '.join(missing)}"))
            return
        coordinates = [value[key] for key in required]
    elif _is_sequence(value) and len(value) == 4:
        coordinates = list(value)
    else:
        violations.append(SchemaViolation(path, "must be a bbox object or four-number array"))
        return

    if any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in coordinates):
        violations.append(SchemaViolation(path, "must contain numeric x0, y0, x1, and y1 coordinates"))
        return
    x0, y0, x1, y1 = coordinates
    if x1 < x0 or y1 < y0:
        violations.append(SchemaViolation(path, "must satisfy x1 >= x0 and y1 >= y0"))


def _required(mapping: Mapping[str, Any], key: str, path: str, violations: list[SchemaViolation]) -> Any:
    if key not in mapping:
        violations.append(SchemaViolation(f"{path}.{key}", "is required"))
        return None
    return mapping[key]


def _require_mapping(value: Any, path: str, violations: list[SchemaViolation]) -> bool:
    if not isinstance(value, Mapping):
        violations.append(SchemaViolation(path, "must be an object"))
        return False
    return True


def _require_sequence(value: Any, path: str, violations: list[SchemaViolation]) -> bool:
    if not _is_sequence(value):
        violations.append(SchemaViolation(path, "must be an array"))
        return False
    return True


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _finish(violations: list[SchemaViolation], raise_on_error: bool) -> list[SchemaViolation]:
    if violations and raise_on_error:
        raise ArtifactSchemaError(violations)
    return violations
