from __future__ import annotations

import hashlib

import pytest
from akilan.canonical_json import (
    canonical_json_bytes,
    canonical_json_fingerprint,
    is_json_compatible,
)


def test_canonical_json_is_order_independent_and_utf8_preserving() -> None:
    first = {"z": [3, {"b": "தமிழ்", "a": True}], "a": 1}
    second = {"a": 1, "z": [3, {"a": True, "b": "தமிழ்"}]}

    first_bytes = canonical_json_bytes(first)
    second_bytes = canonical_json_bytes(second)

    assert first_bytes == second_bytes
    assert "தமிழ்".encode() in first_bytes
    assert b" " not in first_bytes
    assert canonical_json_fingerprint(first) == canonical_json_fingerprint(second)
    assert canonical_json_fingerprint(first) == hashlib.sha256(first_bytes).hexdigest()


def test_json_compatibility_rejects_ambiguous_or_unsupported_values() -> None:
    assert is_json_compatible({"items": [None, True, 1, 1.5, "text"]}) is True
    assert is_json_compatible({1: "non-string-key"}) is False
    assert is_json_compatible({"bytes": b"value"}) is False
    assert is_json_compatible({"set": {"a", "b"}}) is False
    assert is_json_compatible({"nan": float("nan")}) is False
    assert is_json_compatible({"infinity": float("inf")}) is False


@pytest.mark.parametrize(
    "value",
    [
        {1: "non-string-key"},
        {"bytes": b"value"},
        {"nan": float("nan")},
        {"infinity": float("inf")},
    ],
)
def test_canonical_serialization_fails_closed_for_unsupported_values(value: object) -> None:
    with pytest.raises(TypeError, match="canonical JSON contract"):
        canonical_json_bytes(value)
