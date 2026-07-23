"""Deterministic cache identity for PDF artifact builds."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import ExtractionConfig
from .native import sha256_file
from .version import __version__


@dataclass(frozen=True, slots=True)
class ArtifactCacheIdentity:
    """Content-addressed identity for one extraction request."""

    key: str
    source_sha256: str
    schema_version: str
    package_version: str
    configuration: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "source_sha256": self.source_sha256,
            "schema_version": self.schema_version,
            "package_version": self.package_version,
            "configuration": self.configuration,
        }


def _canonical_configuration(config: ExtractionConfig) -> dict[str, Any]:
    config.validate()
    values = asdict(config)
    values.pop("overwrite", None)
    if values.get("page_numbers") is not None:
        values["page_numbers"] = list(values["page_numbers"])
    return values


def build_artifact_cache_identity(
    pdf_path: str | Path,
    config: ExtractionConfig | None = None,
    *,
    schema_version: str = "1.0.0",
    package_version: str = __version__,
) -> ArtifactCacheIdentity:
    """Return a stable cache key for source bytes and semantic extraction inputs.

    Operational controls such as ``overwrite`` are intentionally excluded because
    they do not alter artifact content.
    """

    source = Path(pdf_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if not schema_version.strip():
        raise ValueError("schema_version must not be blank")
    if not package_version.strip():
        raise ValueError("package_version must not be blank")

    configuration = _canonical_configuration(config or ExtractionConfig())
    source_sha256 = sha256_file(source)
    payload = {
        "configuration": configuration,
        "package_version": package_version,
        "schema_version": schema_version,
        "source_sha256": source_sha256,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    key = hashlib.sha256(encoded).hexdigest()
    return ArtifactCacheIdentity(
        key=key,
        source_sha256=source_sha256,
        schema_version=schema_version,
        package_version=package_version,
        configuration=configuration,
    )
