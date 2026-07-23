"""JSON-safe serialization helpers for PyMuPDF and dataclass values."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pymupdf


def to_jsonable(value: Any) -> Any:
    """Recursively convert runtime values to deterministic JSON-compatible data."""

    if dataclasses.is_dataclass(value):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, pymupdf.Rect):
        return [round(float(v), 4) for v in value]
    if isinstance(value, pymupdf.Point):
        return [round(float(value.x), 4), round(float(value.y), 4)]
    if isinstance(value, pymupdf.Matrix):
        return [round(float(v), 6) for v in value]
    if isinstance(value, bytes):
        return {"byte_length": len(value)}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_jsonable(value), indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
