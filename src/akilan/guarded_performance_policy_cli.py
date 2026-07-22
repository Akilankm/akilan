"""Installed command for creating tamper-evident performance policy evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .guarded_performance_evidence_policy import verify_guarded_performance_evidence_policy
from .report_io import write_json_report


def build_parser() -> argparse.ArgumentParser:
    """Build the guarded performance policy parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-performance-policy",
        description=(
            "Verify persisted guarded performance-regression evidence and emit a "
            "tamper-evident operational policy decision."
        ),
    )
    parser.add_argument("evidence", type=Path, help="Persisted guarded performance-regression JSON evidence")
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Destination for deterministic tamper-evident policy-decision evidence",
    )
    parser.add_argument(
        "--require-passed",
        action="store_true",
        help="Reject policy acceptance unless fingerprint-valid regression evidence records passed=true",
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
    """Create policy evidence and return a stable process exit code.

    Exit codes:
    - 0: policy evidence was created and the decision was accepted
    - 1: source evidence was missing, malformed, tampered, or policy-rejected
    - 2: invalid command configuration
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    source = args.evidence.expanduser().resolve()
    report = args.report.expanduser().resolve()
    if source == report:
        parser.error("--report must not overwrite the source regression evidence")

    evidence, source_error = _load_evidence(source)
    if source_error is not None:
        payload = {
            **source_error,
            "decision_accepted": False,
            "report": None,
            "require_passed": args.require_passed,
        }
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    assert evidence is not None
    policy = verify_guarded_performance_evidence_policy(
        evidence,
        require_passed=args.require_passed,
    )
    policy_payload = policy.to_dict()
    report_path = write_json_report(policy_payload, report)
    payload = {
        **policy_payload,
        "source": str(source),
        "report": str(report_path),
    }
    stream = sys.stdout if policy.decision_accepted else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return 0 if policy.decision_accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
