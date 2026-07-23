"""Dependency-free validation for AKILAN artifact manifests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .schema import ArtifactSchemaError, SchemaViolation


def validate_manifest(manifest: Mapping[str, Any], *, raise_on_error: bool = True) -> list[SchemaViolation]:
    """Validate a JSON-decoded ``manifest.json`` and collect all violations."""

    violations: list[SchemaViolation] = []
    if not isinstance(manifest, Mapping):
        violations.append(SchemaViolation("$", "must be an object"))
        return _finish(violations, raise_on_error)

    for key in ("schema_version", "generator", "source", "document", "statistics", "artifact_files", "pages"):
        if key not in manifest:
            violations.append(SchemaViolation(f"$.{key}", "is required"))

    schema_version = manifest.get("schema_version")
    if schema_version is not None and (not isinstance(schema_version, str) or not schema_version.strip()):
        violations.append(SchemaViolation("$.schema_version", "must be a non-empty string"))

    for key in ("generator", "source", "document", "statistics", "artifact_files"):
        value = manifest.get(key)
        if value is not None and not isinstance(value, Mapping):
            violations.append(SchemaViolation(f"$.{key}", "must be an object"))

    pages = manifest.get("pages")
    if pages is not None:
        if not _is_sequence(pages):
            violations.append(SchemaViolation("$.pages", "must be an array"))
        else:
            _validate_pages(pages, violations)

    artifact_files = manifest.get("artifact_files")
    if isinstance(artifact_files, Mapping):
        _validate_artifact_files(artifact_files, violations)

    return _finish(violations, raise_on_error)


def _validate_pages(pages: Sequence[Any], violations: list[SchemaViolation]) -> None:
    observed_numbers: set[int] = set()
    for index, page in enumerate(pages):
        path = f"$.pages[{index}]"
        if not isinstance(page, Mapping):
            violations.append(SchemaViolation(path, "must be an object"))
            continue
        page_number = page.get("page_number")
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number <= 0:
            violations.append(SchemaViolation(f"{path}.page_number", "must be a positive integer"))
        elif page_number in observed_numbers:
            violations.append(SchemaViolation(f"{path}.page_number", f"duplicates page number {page_number}"))
        else:
            observed_numbers.add(page_number)
        for key in ("json_path", "markdown_path", "render_path"):
            value = page.get(key)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                violations.append(SchemaViolation(f"{path}.{key}", "must be null or a non-empty string"))
        metrics = page.get("metrics")
        if metrics is not None and not isinstance(metrics, Mapping):
            violations.append(SchemaViolation(f"{path}.metrics", "must be an object"))


def _validate_artifact_files(files: Mapping[str, Any], violations: list[SchemaViolation]) -> None:
    for key in ("manifest", "document_json"):
        value = files.get(key)
        if not isinstance(value, str) or not value.strip():
            violations.append(SchemaViolation(f"$.artifact_files.{key}", "must be a non-empty string"))
    for key in ("pages", "page_markdown", "images", "renders"):
        value = files.get(key)
        if value is None:
            continue
        if not _is_sequence(value):
            violations.append(SchemaViolation(f"$.artifact_files.{key}", "must be an array"))
            continue
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                violations.append(
                    SchemaViolation(f"$.artifact_files.{key}[{index}]", "must be a non-empty string")
                )


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _finish(violations: list[SchemaViolation], raise_on_error: bool) -> list[SchemaViolation]:
    if violations and raise_on_error:
        raise ArtifactSchemaError(violations)
    return violations
