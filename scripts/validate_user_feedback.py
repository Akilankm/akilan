#!/usr/bin/env python3
"""Validate the AKILAN user feedback queue without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_HEADING = re.compile(
    r"^##\s+(?P<identifier>FB-(?P<number>\d{3,}))\s+"
    r"\[(?P<status>[^\]]+)\]\s*(?P<title>.*)$"
)
_ITEM_PREFIX = re.compile(r"^##\s+FB-")
_ALLOWED_STATUSES = frozenset({"pending", "in_progress", "resolved", "deferred"})


class FeedbackContractError(ValueError):
    """Raised when the feedback queue violates its declared contract."""


def validate_feedback(path: Path) -> dict[str, Any]:
    """Validate a feedback queue and return deterministic machine-readable evidence."""

    path = path.expanduser().resolve()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise FeedbackContractError(f"unreadable feedback file: {exc}") from exc

    items: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    in_fenced_block = False

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fenced_block = not in_fenced_block
            continue
        if in_fenced_block or not _ITEM_PREFIX.match(stripped):
            continue

        match = _HEADING.fullmatch(stripped)
        if match is None:
            raise FeedbackContractError(
                f"line {line_number}: malformed feedback heading; expected "
                "'## FB-001 [pending] Concise title'"
            )

        identifier = match.group("identifier")
        status = match.group("status")
        title = match.group("title").strip()
        number_text = match.group("number")

        if status not in _ALLOWED_STATUSES:
            allowed = ", ".join(sorted(_ALLOWED_STATUSES))
            raise FeedbackContractError(
                f"line {line_number}: unsupported status {status!r}; allowed: {allowed}"
            )
        if not title:
            raise FeedbackContractError(f"line {line_number}: feedback title must not be empty")
        if identifier in seen:
            raise FeedbackContractError(
                f"line {line_number}: duplicate identifier {identifier}; first declared on line {seen[identifier]}"
            )
        if len(number_text) > 3 and number_text.startswith("0"):
            raise FeedbackContractError(
                f"line {line_number}: identifier {identifier} has non-canonical leading zeros"
            )

        seen[identifier] = line_number
        items.append(
            {
                "identifier": identifier,
                "number": int(number_text),
                "status": status,
                "title": title,
                "line": line_number,
            }
        )

    status_counts = {status: 0 for status in sorted(_ALLOWED_STATUSES)}
    for item in items:
        status_counts[item["status"]] += 1

    return {
        "contract_version": "user-feedback-contract-v1",
        "path": str(path),
        "valid": True,
        "item_count": len(items),
        "pending_count": status_counts["pending"],
        "status_counts": status_counts,
        "items": items,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feedback_file", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    try:
        evidence = validate_feedback(args.feedback_file)
    except FeedbackContractError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1

    rendered = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if args.report is not None:
        report = args.report.expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
