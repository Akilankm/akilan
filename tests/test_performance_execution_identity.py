from __future__ import annotations

from dataclasses import replace

import pytest

from akilan.config import ExtractionConfig
from akilan.performance_execution_identity import (
    assess_performance_execution_identity_match,
    build_performance_execution_identity,
)


def test_execution_identity_is_deterministic() -> None:
    config = ExtractionConfig(render_pages=True, render_dpi=200, page_numbers=(1, 3))

    first = build_performance_execution_identity(config)
    second = build_performance_execution_identity(config)

    assert first == second
    assert len(first.fingerprint) == 64
    assert first.to_dict()["extraction_config"]["page_numbers"] == (1, 3)
    assert assess_performance_execution_identity_match(first, second)


def test_execution_identity_changes_with_complete_extraction_config() -> None:
    baseline = build_performance_execution_identity(ExtractionConfig())
    current = build_performance_execution_identity(ExtractionConfig(include_characters=True))

    assert baseline.fingerprint != current.fingerprint
    assert not assess_performance_execution_identity_match(baseline, current)


def test_execution_identity_detects_runtime_difference() -> None:
    baseline = build_performance_execution_identity()
    current = replace(
        baseline,
        python_version="0.0.0",
        fingerprint="0" * 64,
    )

    assert not assess_performance_execution_identity_match(baseline, current)


def test_execution_identity_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="render_dpi"):
        build_performance_execution_identity(ExtractionConfig(render_dpi=10))
