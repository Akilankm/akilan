from __future__ import annotations

import pytest

from akilan.schema_compatibility import (
    SchemaCompatibilityStatus,
    SchemaVersion,
    assess_schema_compatibility,
    parse_schema_version,
)


def test_parse_schema_version_requires_strict_semver_shape() -> None:
    assert parse_schema_version("1.2.3") == SchemaVersion(1, 2, 3)
    assert str(parse_schema_version("0.0.0")) == "0.0.0"

    for value in ("1", "1.2", "1.2.3.4", " 1.2.3", "1.2.3 ", "v1.2.3", "1.-2.3", "1.β.3", ""):
        with pytest.raises(ValueError):
            parse_schema_version(value)


@pytest.mark.parametrize("value", [None, True, 1, 1.0, [], {}])
def test_parse_schema_version_rejects_non_strings(value: object) -> None:
    with pytest.raises(ValueError):
        parse_schema_version(value)


def test_assess_schema_compatibility_accepts_supported_major() -> None:
    report = assess_schema_compatibility("1.99.7")

    assert report.status is SchemaCompatibilityStatus.COMPATIBLE
    assert report.compatible is True
    assert report.to_dict() == {
        "raw_version": "1.99.7",
        "parsed_version": "1.99.7",
        "supported_major": 1,
        "status": "compatible",
        "compatible": True,
        "message": "schema major is supported; run structural validation before consumption",
    }


def test_assess_schema_compatibility_rejects_unsupported_major() -> None:
    report = assess_schema_compatibility("2.0.0")

    assert report.status is SchemaCompatibilityStatus.UNSUPPORTED_MAJOR
    assert report.compatible is False
    assert report.parsed_version == SchemaVersion(2, 0, 0)
    assert report.message == "unsupported schema major 2; expected 1.x.x"


def test_assess_schema_compatibility_reports_invalid_evidence_without_raising() -> None:
    report = assess_schema_compatibility("1.0")

    assert report.status is SchemaCompatibilityStatus.INVALID
    assert report.compatible is False
    assert report.parsed_version is None
    assert report.message == "schema version must use major.minor.patch format"


@pytest.mark.parametrize("supported_major", [-1, True, 1.0, "1"])
def test_assess_schema_compatibility_rejects_invalid_policy(supported_major: object) -> None:
    with pytest.raises(ValueError, match="supported_major"):
        assess_schema_compatibility("1.0.0", supported_major=supported_major)  # type: ignore[arg-type]
