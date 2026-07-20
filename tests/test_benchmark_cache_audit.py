from __future__ import annotations

import json
from pathlib import Path

import pytest
from akilan.benchmark_cache_audit import (
    audit_benchmark_cache,
    write_benchmark_cache_audit_report,
)
from akilan.benchmark_cache_validation import BenchmarkCacheViolation


def _marker(directory: Path) -> None:
    directory.mkdir(parents=True)
    (directory / ".akilan-benchmark-cache.json").write_text("{}\n", encoding="utf-8")


def test_audit_discovers_entries_in_stable_relative_path_order(tmp_path: Path, monkeypatch) -> None:
    _marker(tmp_path / "zeta")
    _marker(tmp_path / "nested" / "alpha")
    seen: list[str] = []

    def validate(path: Path):
        seen.append(path.relative_to(tmp_path).as_posix())
        return []

    monkeypatch.setattr("akilan.benchmark_cache_audit.validate_benchmark_cache_entry", validate)

    report = audit_benchmark_cache(tmp_path)

    assert [entry.artifact_dir for entry in report.entries] == ["nested/alpha", "zeta"]
    assert seen == ["nested/alpha", "zeta"]
    assert report.passed is True
    assert report.valid_entries == 2
    assert report.invalid_entries == 0


def test_audit_preserves_deterministic_violation_evidence(tmp_path: Path, monkeypatch) -> None:
    _marker(tmp_path / "broken")
    violation = BenchmarkCacheViolation("$.cache.identity", "does not match")
    monkeypatch.setattr(
        "akilan.benchmark_cache_audit.validate_benchmark_cache_entry",
        lambda path: [violation],
    )

    first = audit_benchmark_cache(tmp_path)
    second = audit_benchmark_cache(tmp_path)

    assert first == second
    assert first.passed is False
    assert first.invalid_entries == 1
    assert first.to_dict()["entries"][0]["violations"] == [violation.to_dict()]
    assert len(first.to_dict()["report_fingerprint"]) == 64
    assert first.to_dict()["report_fingerprint"] == second.to_dict()["report_fingerprint"]


def test_empty_or_missing_cache_root_fails_closed(tmp_path: Path) -> None:
    empty = audit_benchmark_cache(tmp_path)
    missing = audit_benchmark_cache(tmp_path / "missing")

    assert empty.entries == ()
    assert empty.passed is False
    assert missing.entries == ()
    assert missing.passed is False


def test_non_directory_root_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "file"
    path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        audit_benchmark_cache(path)


def test_report_writer_emits_stable_json_with_trailing_newline(tmp_path: Path, monkeypatch) -> None:
    _marker(tmp_path / "cache" / "case")
    monkeypatch.setattr(
        "akilan.benchmark_cache_audit.validate_benchmark_cache_entry",
        lambda path: [],
    )
    report = audit_benchmark_cache(tmp_path / "cache")

    destination = write_benchmark_cache_audit_report(
        report,
        tmp_path / "reports" / "benchmark-cache-audit.json",
    )
    text = destination.read_text(encoding="utf-8")

    assert text.endswith("\n")
    assert json.loads(text) == report.to_dict()
