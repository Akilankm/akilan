from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def test_ci_uses_guarded_benchmark_and_persists_source_evidence() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "akilan-guarded-benchmark artifacts/ci-corpus" in workflow
    assert "--guard-report artifacts/ci-benchmark/source-guard.json" in workflow
    assert "akilan benchmark artifacts/ci-corpus" not in workflow


def test_ci_uploads_guard_evidence_with_benchmark_bundle() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "artifacts/ci-benchmark" in workflow
    assert "if-no-files-found: error" in workflow
