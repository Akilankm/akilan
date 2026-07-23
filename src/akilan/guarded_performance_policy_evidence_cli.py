"""Installed command for verifying persisted performance policy evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .guarded_performance_evidence_policy import verify_guarded_performance_policy_evidence
from .report_io import write_json_report


def build_parser() -> argparse.ArgumentParser:
    """Build the guarded performance policy evidence verification parser."""

    parser = argparse.ArgumentParser(
        prog="akilan-verify-performance-policy-evidence",
        description=(
            "Verify the canonical SHA-256 fingerprint of persisted guarded "
            "performance policy-decision evidence and optionally require the "
            "recorded policy decision to have been accepted."
        ),
    )
    parser.add_argument("evidence", type=Path, help="Persisted guarded performance policy JSON evidence")
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for deterministic machine-readable verification evidence",
    )
    parser.add_argument(
        "--require-accepted",
        action="store_true",
        help=(
            "Return exit code 1 unless fingerprint-valid policy evidence records "
            "decision_accepted=true. This does not reinterpret the policy decision."
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
    """Verify persisted policy evidence and return a stable process exit code.

    Exit codes:
    - 0: fingerprint-valid evidence satisfying any requested acceptance policy
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
            "require_accepted": args.require_accepted,
            "recorded_decision_accepted": None,
            "operationally_accepted": False,
        }
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        return 1

    assert evidence is not None
    verification = verify_guarded_performance_policy_evidence(evidence)
    raw_decision = evidence.get("decision_accepted")
    recorded_decision_accepted = raw_decision if isinstance(raw_decision, bool) else None
    operationally_accepted = verification.valid and (
        not args.require_accepted or recorded_decision_accepted is True
    )

    if not verification.valid:
        operational_status = verification.status
    elif not args.require_accepted:
        operational_status = "valid"
    elif recorded_decision_accepted is True:
        operational_status = "accepted"
    elif recorded_decision_accepted is False:
        operational_status = "recorded_policy_rejected"
    else:
        operational_status = "recorded_policy_decision_missing"

    report_payload = {
        **verification.to_dict(),
        "operational_status": operational_status,
        "require_accepted": args.require_accepted,
        "recorded_decision_accepted": recorded_decision_accepted,
        "operationally_accepted": operationally_accepted,
    }
    report_path: Path | None = None
    if args.report is not None:
        report_path = write_json_report(report_payload, args.report)

    payload = {
        **report_payload,
        "source": str(args.evidence.expanduser().resolve()),
        "report": str(report_path) if report_path is not None else None,
    }
    stream = sys.stdout if operationally_accepted else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return 0 if operationally_accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
