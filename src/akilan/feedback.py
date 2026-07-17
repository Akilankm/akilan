"""Parse repository-local user feedback into actionable development items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_PENDING = "pending"
_SUPPORTED_STATUSES = {_PENDING, "in_progress", "resolved", "deferred"}


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
    the next level-two heading. Unknown statuses fail fast so automation cannot
    silently ignore malformed workflow state.
    """

    feedback_path = Path(path)
    if not feedback_path.exists():
        return ()

    items: list[FeedbackItem] = []
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

    for raw_line in feedback_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            flush()
            heading = line[3:].strip()
            try:
                identifier, remainder = heading.split(" ", 1)
                status_token, title = remainder.split(" ", 1)
            except ValueError as exc:
                raise ValueError(f"Invalid feedback heading: {line}") from exc
            if not (status_token.startswith("[") and status_token.endswith("]")):
                raise ValueError(f"Missing feedback status: {line}")
            status = status_token[1:-1].strip().lower()
            if status not in _SUPPORTED_STATUSES:
                raise ValueError(f"Unsupported feedback status {status!r}: {line}")
            current = (identifier.strip(), status, title.strip())
        elif current is not None and line and not line.startswith("<!--"):
            details.append(line)

    flush()
    return tuple(items)


def pending_feedback(path: str | Path = "user_feedback.md") -> tuple[FeedbackItem, ...]:
    """Return feedback that is ready for the next development cycle."""

    return tuple(item for item in load_feedback(path) if item.status == _PENDING)
