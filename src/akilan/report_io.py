"""Durable helpers for publishing machine-readable AKILAN reports."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def write_json_report(payload: Any, destination: str | Path) -> Path:
    """Atomically persist deterministic JSON and return the resolved path.

    The payload is written to a temporary file in the destination directory,
    flushed to disk, and then moved into place with ``os.replace``. Existing
    reports therefore remain readable until the replacement is complete.
    Temporary files are removed when serialization or publication fails.
    """

    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return path
