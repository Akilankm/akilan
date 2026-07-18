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
_MIRRORED_DOCUMENT_FIELDS = ("schema_version", "generator", "source", "document", "statistics")


def validate_artifact_directory(
    artifact_dir: str | Path,
    *,
    raise_on_error: bool = True,
) -> list[SchemaViolation]:
    """Validate a persisted artifact directory and all manifest-declared files.

    The check is read-only and aggregates structural, path-safety, existence,
    JSON-contract, and cross-file consistency violations. It does not repair,
    delete, or rewrite artifacts.
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
    document: Mapping[str, Any] | None = None
    page_documents: list[Mapping[str, Any] | None] = []

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
            loaded_document = _load_json(resolved_document, "$.document_json", violations)
            if isinstance(loaded_document, Mapping):
                document = loaded_document
                violations.extend(validate_artifact(document, raise_on_error=False))
            elif loaded_document is not None:
                violations.append(SchemaViolation("$.document_json", "must contain a JSON object"))

        page_paths = artifact_files.get("pages")
        if _is_sequence(page_paths):
            for index, value in enumerate(page_paths):
                resolved_page = _safe_declared_path(root, value)
                page_document: Mapping[str, Any] | None = None
                if resolved_page is not None and resolved_page.is_file():
                    page = _load_json(resolved_page, f"$.page_json[{index}]", violations)
                    if isinstance(page, Mapping):
                        page_document = page
                    elif page is not None:
                        violations.append(SchemaViolation(f"$.page_json[{index}]", "must contain a JSON object"))
                page_documents.append(page_document)

    if document is not None:
        _validate_manifest_document_consistency(manifest, document, violations)
        _validate_page_file_consistency(document, artifact_files, page_documents, violations)

    return _finish(violations, raise_on_error)


def _validate_manifest_document_consistency(
    manifest: Mapping[str, Any],
    document: Mapping[str, Any],
    violations: list[SchemaViolation],
) -> None:
    for field in _MIRRORED_DOCUMENT_FIELDS:
        if manifest.get(field) != document.get(field):
            violations.append(
                SchemaViolation(
                    f"$.manifest.{field}",
                    f"must exactly match document.json field {field!r}",
                )
            )

    manifest_files = manifest.get("artifact_files")
    document_files = document.get("artifact_files")
    if isinstance(manifest_files, Mapping) and isinstance(document_files, Mapping):
        for field in (*_SCALAR_ARTIFACT_PATHS, *_SEQUENCE_ARTIFACT_PATHS):
            if field == "document_json":
                continue
            if manifest_files.get(field) != document_files.get(field):
                violations.append(
                    SchemaViolation(
                        f"$.manifest.artifact_files.{field}",
                        f"must exactly match document.json artifact_files.{field}",
                    )
                )

    manifest_pages = manifest.get("pages")
    document_pages = document.get("pages")
    if not _is_sequence(manifest_pages) or not _is_sequence(document_pages):
        return
    if len(manifest_pages) != len(document_pages):
        violations.append(
            SchemaViolation(
                "$.manifest.pages",
                f"page count {len(manifest_pages)} does not match document.json page count {len(document_pages)}",
            )
        )
        return

    for index, (manifest_page, document_page) in enumerate(zip(manifest_pages, document_pages, strict=True)):
        if not isinstance(manifest_page, Mapping) or not isinstance(document_page, Mapping):
            continue
        for field in ("page_number", "label", "json_path", "markdown_path", "render_path", "metrics"):
            if manifest_page.get(field) != document_page.get(field):
                violations.append(
                    SchemaViolation(
                        f"$.manifest.pages[{index}].{field}",
                        f"must exactly match document.json pages[{index}].{field}",
                    )
                )


def _validate_page_file_consistency(
    document: Mapping[str, Any],
    artifact_files: Any,
    page_documents: list[Mapping[str, Any] | None],
    violations: list[SchemaViolation],
) -> None:
    canonical_pages = document.get("pages")
    if not _is_sequence(canonical_pages) or not isinstance(artifact_files, Mapping):
        return

    declared_paths = artifact_files.get("pages")
    if _is_sequence(declared_paths) and len(declared_paths) != len(canonical_pages):
        violations.append(
            SchemaViolation(
                "$.artifact_files.pages",
                f"declares {len(declared_paths)} page files for {len(canonical_pages)} canonical pages",
            )
        )

    for index, canonical_page in enumerate(canonical_pages):
        if not isinstance(canonical_page, Mapping):
            continue
        if index < len(page_documents):
            page_document = page_documents[index]
            if page_document is not None and page_document != canonical_page:
                violations.append(
                    SchemaViolation(
                        f"$.page_json[{index}]",
                        f"must exactly match document.json pages[{index}]",
                    )
                )
        if _is_sequence(declared_paths) and index < len(declared_paths):
            expected_path = canonical_page.get("json_path")
            if declared_paths[index] != expected_path:
                violations.append(
                    SchemaViolation(
                        f"$.artifact_files.pages[{index}]",
                        f"must match document.json pages[{index}].json_path",
                    )
                )


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
