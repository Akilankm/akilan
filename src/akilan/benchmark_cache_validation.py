"""Read-only integrity checks for benchmark cache entries."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifact_directory import validate_artifact_directory

BENCHMARK_CACHE_FILENAME = ".akilan-benchmark-cache.json"
BENCHMARK_CACHE_FORMAT_VERSION = 1
BENCHMARK_CACHE_RULE_ID = "benchmark-cache-integrity-v1"
_REQUIRED_METRIC_FIELDS = {
    "artifact_fingerprint",
    "page_count",
    "source_sha256",
}


@dataclass(frozen=True, slots=True)
class BenchmarkCacheViolation:
    """One deterministic benchmark-cache integrity violation."""

    path: str
    message: str
    rule_id: str = BENCHMARK_CACHE_RULE_ID

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "message": self.message,
            "rule_id": self.rule_id,
        }


def validate_benchmark_cache_entry(
    artifact_dir: str | Path,
    *,
    expected_identity: str | None = None,
) -> list[BenchmarkCacheViolation]:
    """Return deterministic violations for one persisted benchmark cache entry.

    A reusable benchmark cache entry must contain a supported marker contract, a
    valid request identity, a complete canonical artifact directory, and cached
    metrics that agree with the persisted document identity and canonical content.
    The function is read-only and never repairs or removes cache state.
    """

    root = Path(artifact_dir).expanduser().resolve()
    violations: list[BenchmarkCacheViolation] = []
    marker_path = root / BENCHMARK_CACHE_FILENAME

    marker = _load_mapping(marker_path, "$.cache", violations)
    if marker is None:
        return _sorted(violations)

    _validate_marker_contract(marker, expected_identity, violations)

    metrics = marker.get("metrics")
    if not isinstance(metrics, Mapping):
        violations.append(BenchmarkCacheViolation("$.cache.metrics", "must be an object"))
        metrics = None
    else:
        for field in sorted(_REQUIRED_METRIC_FIELDS):
            if field not in metrics:
                violations.append(BenchmarkCacheViolation(f"$.cache.metrics.{field}", "is required"))
        _validate_metric_shapes(metrics, violations)

    for schema_violation in validate_artifact_directory(root, raise_on_error=False):
        violations.append(
            BenchmarkCacheViolation(
                f"$.artifact{schema_violation.path[1:] if schema_violation.path.startswith('$') else '.' + schema_violation.path}",
                schema_violation.message,
            )
        )

    document = _load_mapping(root / "document.json", "$.artifact.document", violations)
    if metrics is not None and document is not None:
        _validate_metric_consistency(metrics, document, violations)

    return _sorted(violations)


def _validate_marker_contract(
    marker: Mapping[str, Any],
    expected_identity: str | None,
    violations: list[BenchmarkCacheViolation],
) -> None:
    format_version = marker.get("cache_format_version")
    if isinstance(format_version, bool) or not isinstance(format_version, int):
        violations.append(BenchmarkCacheViolation("$.cache.cache_format_version", "must be an integer"))
    elif format_version != BENCHMARK_CACHE_FORMAT_VERSION:
        violations.append(
            BenchmarkCacheViolation(
                "$.cache.cache_format_version",
                f"unsupported version {format_version}; expected {BENCHMARK_CACHE_FORMAT_VERSION}",
            )
        )

    identity = marker.get("identity")
    if not _is_sha256(identity):
        violations.append(
            BenchmarkCacheViolation(
                "$.cache.identity",
                "must be a lowercase 64-character SHA-256 digest",
            )
        )
    elif expected_identity is not None and identity != expected_identity:
        violations.append(
            BenchmarkCacheViolation(
                "$.cache.identity",
                "does not match the expected benchmark request identity",
            )
        )


def _validate_metric_shapes(
    metrics: Mapping[str, Any],
    violations: list[BenchmarkCacheViolation],
) -> None:
    source_sha = metrics.get("source_sha256")
    if "source_sha256" in metrics and not _is_sha256(source_sha):
        violations.append(
            BenchmarkCacheViolation(
                "$.cache.metrics.source_sha256",
                "must be a lowercase 64-character SHA-256 digest",
            )
        )

    page_count = metrics.get("page_count")
    if "page_count" in metrics and (
        isinstance(page_count, bool) or not isinstance(page_count, int) or page_count < 0
    ):
        violations.append(
            BenchmarkCacheViolation(
                "$.cache.metrics.page_count",
                "must be a non-negative integer",
            )
        )

    fingerprint = metrics.get("artifact_fingerprint")
    if "artifact_fingerprint" in metrics and not _is_sha256(fingerprint):
        violations.append(
            BenchmarkCacheViolation(
                "$.cache.metrics.artifact_fingerprint",
                "must be a lowercase 64-character SHA-256 digest",
            )
        )


def _validate_metric_consistency(
    metrics: Mapping[str, Any],
    document: Mapping[str, Any],
    violations: list[BenchmarkCacheViolation],
) -> None:
    source = document.get("source")
    document_sha = source.get("sha256") if isinstance(source, Mapping) else None
    if metrics.get("source_sha256") != document_sha:
        violations.append(
            BenchmarkCacheViolation(
                "$.cache.metrics.source_sha256",
                "must match document.json source.sha256",
            )
        )

    pages = document.get("pages")
    document_page_count = len(pages) if isinstance(pages, list) else None
    if metrics.get("page_count") != document_page_count:
        violations.append(
            BenchmarkCacheViolation(
                "$.cache.metrics.page_count",
                "must match the number of pages in document.json",
            )
        )

    persisted_fingerprint = _canonical_mapping_fingerprint(document)
    if metrics.get("artifact_fingerprint") != persisted_fingerprint:
        violations.append(
            BenchmarkCacheViolation(
                "$.cache.metrics.artifact_fingerprint",
                "must match the canonical fingerprint of document.json",
            )
        )


def _canonical_mapping_fingerprint(document: Mapping[str, Any]) -> str:
    payload = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _load_mapping(
    path: Path,
    location: str,
    violations: list[BenchmarkCacheViolation],
) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        violations.append(BenchmarkCacheViolation(location, f"file is missing: {path.name}"))
        return None
    except OSError as exc:
        violations.append(BenchmarkCacheViolation(location, f"cannot read file: {exc}"))
        return None
    except json.JSONDecodeError as exc:
        violations.append(
            BenchmarkCacheViolation(
                location,
                f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            )
        )
        return None

    if not isinstance(payload, Mapping):
        violations.append(BenchmarkCacheViolation(location, "must contain a JSON object"))
        return None
    return payload


def _sorted(violations: list[BenchmarkCacheViolation]) -> list[BenchmarkCacheViolation]:
    return sorted(violations, key=lambda violation: (violation.path, violation.message, violation.rule_id))
