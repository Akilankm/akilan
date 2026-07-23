from __future__ import annotations

import json
from pathlib import Path

from akilan.benchmark_cache_audit import (
    BenchmarkCacheAuditEntry,
    BenchmarkCacheAuditReport,
)
from akilan.benchmark_cache_validation import BenchmarkCacheViolation
from akilan.cli import main


def test_audit_benchmark_cache_command_reports_pass_and_writes_report(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = tmp_path / "cache"
    destination = tmp_path / "reports" / "audit.json"
    report = BenchmarkCacheAuditReport(
        root=str(root.resolve()),
        entries=(BenchmarkCacheAuditEntry("case-a"),),
    )
    monkeypatch.setattr("akilan.cli.audit_benchmark_cache", lambda path: report)

    exit_code = main(
        ["audit-benchmark-cache", str(root), "--report", str(destination)]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["summary"] == {
        "total": 1,
        "valid": 1,
        "invalid": 0,
        "passed": True,
    }
    assert payload["report"] == str(destination.resolve())
    assert json.loads(destination.read_text(encoding="utf-8")) == report.to_dict()


def test_audit_benchmark_cache_command_fails_closed_with_violation_evidence(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    root = tmp_path / "cache"
    violation = BenchmarkCacheViolation("$.cache.metrics.page_count", "does not match")
    report = BenchmarkCacheAuditReport(
        root=str(root.resolve()),
        entries=(BenchmarkCacheAuditEntry("broken", (violation,)),),
    )
    monkeypatch.setattr("akilan.cli.audit_benchmark_cache", lambda path: report)

    exit_code = main(["audit-benchmark-cache", str(root)])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exit_code == 1
    assert captured.out == ""
    assert payload["summary"]["passed"] is False
    assert payload["entries"][0]["violations"] == [violation.to_dict()]
    assert payload["report"] is None


def test_audit_benchmark_cache_command_rejects_file_root(
    tmp_path: Path,
    capsys,
) -> None:
    root = tmp_path / "not-a-directory"
    root.write_text("content", encoding="utf-8")

    exit_code = main(["audit-benchmark-cache", str(root)])

    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert exit_code == 1
    assert captured.out == ""
    assert payload["root"] == str(root.resolve())
    assert payload["summary"]["passed"] is False
    assert payload["error"] == "benchmark cache root is not a directory"
