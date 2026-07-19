"""Parse repository-local user feedback into actionable development items."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PENDING = "pending"
_SUPPORTED_STATUSES = {_PENDING, "in_progress", "resolved", "deferred"}
_IDENTIFIER_PATTERN = re.compile(r"^FB-[0-9]{3,}$")


@dataclass(frozen=True, slots=True)
class FeedbackItem:
    """One auditable feedback request from ``user_feedback.md``."""

    identifier: str
    status: str
    title: str
    details: tuple[str, ...]


def load_feedback(path: str | Path = "user_feedback.md") -> tuple[FeedbackItem, ...]:
    """Load feedback items from a constrained Markdown format.

    Items start with a level-two heading in the form::

        ## FB-001 [pending] Short title

    Free-form non-empty lines below the heading are retained as details until
    the next level-two heading. Unknown statuses, malformed identifiers, empty
    titles, and duplicate identifiers fail fast so automation cannot silently
    ignore or ambiguously process repository-local feedback.
    """

    feedback_path = Path(path)
    if not feedback_path.exists():
        return ()

    items: list[FeedbackItem] = []
    seen_identifiers: set[str] = set()
    current: tuple[str, str, str] | None = None
    details: list[str] = []

    def flush() -> None:
        nonlocal current, details
        if current is None:
            return
        identifier, status, title = current
        items.append(FeedbackItem(identifier, status, title, tuple(details)))
        current = None
        details = []

    for line_number, raw_line in enumerate(
        feedback_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if line.startswith("## "):
            flush()
            heading = line[3:].strip()
            try:
                identifier, remainder = heading.split(" ", 1)
                status_token, title = remainder.split(" ", 1)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid feedback heading at line {line_number}: {line}"
                ) from exc
            identifier = identifier.strip()
            title = title.strip()
            if not _IDENTIFIER_PATTERN.fullmatch(identifier):
                raise ValueError(
                    f"Invalid feedback identifier {identifier!r} at line {line_number}"
                )
            if identifier in seen_identifiers:
                raise ValueError(
                    f"Duplicate feedback identifier {identifier!r} at line {line_number}"
                )
            if not (status_token.startswith("[") and status_token.endswith("]")):
                raise ValueError(f"Missing feedback status at line {line_number}: {line}")
            status = status_token[1:-1].strip().lower()
            if status not in _SUPPORTED_STATUSES:
                raise ValueError(
                    f"Unsupported feedback status {status!r} at line {line_number}: {line}"
                )
            if not title:
                raise ValueError(
                    f"Missing feedback title for {identifier!r} at line {line_number}"
                )
            seen_identifiers.add(identifier)
            current = (identifier, status, title)
        elif current is not None and line and not line.startswith("<!--"):
            details.append(line)

    flush()
    return tuple(items)


def pending_feedback(path: str | Path = "user_feedback.md") -> tuple[FeedbackItem, ...]:
    """Return feedback that is ready for the next development cycle."""

    return tuple(item for item in load_feedback(path) if item.status == _PENDING)
