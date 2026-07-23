"""Installed command for verifying persisted guarded performance decision evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .guarded_performance_regression import verify_guarded_performance_regression_evidence
from .report_io import write_json_report


def build_parser() -> argparse.ArgumentParser:
    """Build the guarded performance evidence verification parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-verify-performance-evidence",
        description=(
            "Verify the canonical SHA-256 fingerprint of a persisted guarded "
            "performance-regression decision and optionally require the recorded "
            "decision to have passed."
        ),
    )
    parser.add_argument("evidence", type=Path, help="Persisted guarded regression JSON evidence")
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for deterministic machine-readable verification evidence",
    )
    parser.add_argument(
        "--require-passed",
        action="store_true",
        help=(
            "Return exit code 1 unless fingerprint-valid evidence records passed=true. "
            "This does not recompute or override the decision."
        ),
    )
    return parser


def _load_evidence(path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        return None, {"valid": False, "status": "missing", "source": str(resolved)}
    if not resolved.is_file():
        return None, {"valid": False, "status": "not_a_file", "source": str(resolved)}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, {"valid": False, "status": "invalid_json", "source": str(resolved)}
    if not isinstance(value, dict):
        return None, {"valid": False, "status": "invalid_root", "source": str(resolved)}
    return value, None


def main(argv: list[str] | None = None) -> int:
    """Verify persisted evidence and return a stable process exit code.

    Exit codes:
    - 0: fingerprint-valid evidence satisfying any requested decision policy
    - 1: missing, malformed, fingerprint-invalid, or policy-rejected evidence
    - 2: invalid command configuration
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    evidence, source_error = _load_evidence(args.evidence)
    if source_error is not None:
        payload = {
            **source_error,
            "report": None,
            "require_passed": args.require_passed,
            "decision_accepted": False,
        }
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    assert evidence is not None
    verification = verify_guarded_performance_regression_evidence(evidence)
    recorded_decision = evidence.get("passed")
    decision_is_boolean = isinstance(recorded_decision, bool)
    decision_accepted = verification.valid and (
        not args.require_passed or (decision_is_boolean and recorded_decision)
    )
    operational_status = verification.status
    if verification.valid and args.require_passed:
        if recorded_decision is True:
            operational_status = "accepted"
        elif decision_is_boolean:
            operational_status = "recorded_decision_failed"
        else:
            operational_status = "recorded_decision_missing"

    report_payload = {
        **verification.to_dict(),
        "operational_status": operational_status,
        "require_passed": args.require_passed,
        "recorded_decision": recorded_decision,
        "decision_accepted": decision_accepted,
    }
    report_path: Path | None = None
    if args.report is not None:
        report_path = write_json_report(report_payload, args.report)

    payload = {
        **report_payload,
        "source": str(args.evidence.expanduser().resolve()),
        "report": str(report_path) if report_path is not None else None,
    }
    stream = sys.stdout if decision_accepted else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return 0 if decision_accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
