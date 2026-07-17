from __future__ import annotations

from pathlib import Path

import pytest

from akilan.feedback import load_feedback, pending_feedback


def test_feedback_parser_preserves_pending_items(tmp_path: Path) -> None:
    path = tmp_path / "user_feedback.md"
    path.write_text(
        """# User Feedback

## FB-001 [pending] Handle encrypted PDFs
- Reproduce with `data/encrypted.pdf`.
- Emit a precise error.

## FB-002 [resolved] Add notebook
Completed in PR #10.
""",
        encoding="utf-8",
    )

    items = load_feedback(path)

    assert [item.identifier for item in items] == ["FB-001", "FB-002"]
    assert items[0].details == (
        "- Reproduce with `data/encrypted.pdf`.",
        "- Emit a precise error.",
    )
    assert [item.identifier for item in pending_feedback(path)] == ["FB-001"]


def test_feedback_parser_rejects_unknown_status(tmp_path: Path) -> None:
    path = tmp_path / "user_feedback.md"
    path.write_text("## FB-001 [unknown] Invalid state\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported feedback status"):
        load_feedback(path)


def test_missing_feedback_file_is_empty(tmp_path: Path) -> None:
    assert load_feedback(tmp_path / "missing.md") == ()
