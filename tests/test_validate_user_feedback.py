from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_user_feedback.py"
_SPEC = importlib.util.spec_from_file_location("validate_user_feedback", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_validate_feedback_accepts_template_and_real_items(tmp_path: Path) -> None:
    feedback = _write(
        tmp_path / "user_feedback.md",
        """# Queue

```markdown
## FB-001 [pending] Template item
```

## FB-002 [pending] Extraction failed on rotated page
- Error: boom

## FB-003 [resolved] Preserve original evidence
""",
    )

    evidence = _MODULE.validate_feedback(feedback)

    assert evidence["valid"] is True
    assert evidence["item_count"] == 2
    assert evidence["pending_count"] == 1
    assert [item["identifier"] for item in evidence["items"]] == ["FB-002", "FB-003"]


def test_validate_feedback_rejects_duplicate_identifier(tmp_path: Path) -> None:
    feedback = _write(
        tmp_path / "user_feedback.md",
        """## FB-001 [pending] First
## FB-001 [resolved] Duplicate
""",
    )

    try:
        _MODULE.validate_feedback(feedback)
    except _MODULE.FeedbackContractError as exc:
        assert "duplicate identifier FB-001" in str(exc)
        assert "line 2" in str(exc)
    else:
        raise AssertionError("expected duplicate identifier failure")


def test_validate_feedback_rejects_malformed_or_unsupported_heading(tmp_path: Path) -> None:
    malformed = _write(tmp_path / "malformed.md", "## FB-001 pending Missing brackets\n")
    unsupported = _write(tmp_path / "unsupported.md", "## FB-001 [done] Unsupported\n")

    for path, expected in (
        (malformed, "malformed feedback heading"),
        (unsupported, "unsupported status"),
    ):
        try:
            _MODULE.validate_feedback(path)
        except _MODULE.FeedbackContractError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"expected contract failure for {path.name}")


def test_validate_feedback_rejects_empty_title_and_noncanonical_identifier(tmp_path: Path) -> None:
    empty_title = _write(tmp_path / "empty.md", "## FB-001 [pending]\n")
    leading_zero = _write(tmp_path / "leading-zero.md", "## FB-0001 [pending] Bad identifier\n")

    for path, expected in (
        (empty_title, "title must not be empty"),
        (leading_zero, "non-canonical leading zeros"),
    ):
        try:
            _MODULE.validate_feedback(path)
        except _MODULE.FeedbackContractError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"expected contract failure for {path.name}")
