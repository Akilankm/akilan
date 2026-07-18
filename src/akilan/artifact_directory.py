"""Dependency-free integrity checks for persisted AKILAN artifact directories."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from .manifest_schema import validate_manifest
from .schema import ArtifactSchemaError, SchemaViolation, validate_artifact

_SCALAR_ARTIFACT_PATHS = ("manifest", "document_json", "document_markdown", "plain_text")
_SEQUENCE_ARTIFACT_PATHS = ("pages", "page_markdown", "images", "renders")


def validate_artifact_directory(
    artifact_dir: str | Path,
    *,
    raise_on_error: bool = True,
) -> list[SchemaViolation]:
    """Validate a persisted artifact directory and all manifest-declared files.

    The check is read-only and aggregates structural, path-safety, existence, and
    JSON-contract violations. It does not repair, delete, or rewrite artifacts.
    """

    root = Path(artifact_dir).expanduser().resolve()
    violations: list[SchemaViolation] = []
    if not root.is_dir():
        violations.append(SchemaViolation("$", f"artifact directory does not exist: {root}"))
        return _finish(violations, raise_on_error)

    manifest_path = root / "manifest.json"
    manifest = _load_json(manifest_path, "$.manifest", violations)
    if not isinstance(manifest, Mapping):
        if manifest is not None:
            violations.append(SchemaViolation("$.manifest", "must contain a JSON object"))
        return _finish(violations, raise_on_error)

    violations.extend(validate_manifest(manifest, raise_on_error=False))
    artifact_files = manifest.get("artifact_files")
    if isinstance(artifact_files, Mapping):
        for key in _SCALAR_ARTIFACT_PATHS:
            value = artifact_files.get(key)
            if value is not None:
                _validate_declared_file(root, value, f"$.artifact_files.{key}", violations)
        for key in _SEQUENCE_ARTIFACT_PATHS:
            values = artifact_files.get(key)
            if _is_sequence(values):
                for index, value in enumerate(values):
                    _validate_declared_file(root, value, f"$.artifact_files.{key}[{index}]", violations)

        document_path = artifact_files.get("document_json")
        resolved_document = _safe_declared_path(root, document_path)
        if resolved_document is not None and resolved_document.is_file():
            document = _load_json(resolved_document, "$.document_json", violations)
            if isinstance(document, Mapping):
                violations.extend(validate_artifact(document, raise_on_error=False))
            elif document is not None:
                violations.append(SchemaViolation("$.document_json", "must contain a JSON object"))

        page_paths = artifact_files.get("pages")
        if _is_sequence(page_paths):
            for index, value in enumerate(page_paths):
                resolved_page = _safe_declared_path(root, value)
                if resolved_page is not None and resolved_page.is_file():
                    page = _load_json(resolved_page, f"$.page_json[{index}]", violations)
                    if page is not None and not isinstance(page, Mapping):
                        violations.append(
                            SchemaViolation(f"$.page_json[{index}]", "must contain a JSON object")
                        )

    return _finish(violations, raise_on_error)


def _validate_declared_file(
    root: Path,
    value: Any,
    path: str,
    violations: list[SchemaViolation],
) -> None:
    resolved = _safe_declared_path(root, value)
    if resolved is None:
        violations.append(SchemaViolation(path, "must be a safe non-empty relative POSIX path"))
        return
    if not resolved.is_file():
        violations.append(SchemaViolation(path, f"declared artifact file is missing: {value}"))


def _safe_declared_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        return None
    candidate = (root / Path(*pure.parts)).resolve()
    if not candidate.is_relative_to(root):
        return None
    return candidate


def _load_json(path: Path, location: str, violations: list[SchemaViolation]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        violations.append(SchemaViolation(location, f"file is missing: {path.name}"))
    except OSError as exc:
        violations.append(SchemaViolation(location, f"cannot read file: {exc}"))
    except json.JSONDecodeError as exc:
        violations.append(
            SchemaViolation(location, f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        )
    return None


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _finish(violations: list[SchemaViolation], raise_on_error: bool) -> list[SchemaViolation]:
    if violations and raise_on_error:
        raise ArtifactSchemaError(violations)
    return violations
