"""Safe loading for persisted AKILAN artifact directories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact_directory import validate_artifact_directory


def load_artifact_directory(artifact_dir: str | Path) -> dict[str, Any]:
    """Validate and load the canonical document artifact from ``artifact_dir``.

    Validation is completed before any artifact payload is returned. This keeps
    downstream consumers from accepting incomplete, malformed, or path-unsafe
    artifact directories. The returned mapping is detached from the files on
    disk and may be mutated by the caller without changing persisted content.
    """

    root = Path(artifact_dir).expanduser().resolve()
    validate_artifact_directory(root)

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    document_path = manifest["artifact_files"]["document_json"]
    document = json.loads((root / document_path).read_text(encoding="utf-8"))
    return document
