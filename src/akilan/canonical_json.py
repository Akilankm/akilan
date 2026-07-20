"""Canonical JSON serialization and fingerprints for persisted contracts."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a JSON-compatible value using AKILAN's canonical byte contract.

    The representation is independent of mapping insertion order and formatting:
    keys are recursively sorted, separators are compact, and Unicode text is
    encoded directly as UTF-8 rather than escaped to ASCII. Unsupported values and
    non-finite floats are rejected before serialization.
    """

    if not is_json_compatible(value):
        raise TypeError("value is not compatible with the canonical JSON contract")
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_fingerprint(value: Any) -> str:
    """Return the lowercase SHA-256 digest of canonical JSON content."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def is_json_compatible(value: Any) -> bool:
    """Return whether ``value`` can be represented by the canonical contract.

    This helper is intentionally conservative and rejects non-string mapping keys,
    non-finite floats, bytes, sets, and arbitrary objects.
    """

    if value is None or isinstance(value, str | bool | int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(
            isinstance(key, str) and is_json_compatible(item)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return all(is_json_compatible(item) for item in value)
    return False
