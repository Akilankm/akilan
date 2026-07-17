# AKILAN User Feedback Queue

Use this file to record errors, feature requests, validation observations, and enterprise requirements discovered while testing the latest merged development branch.

## Workflow

1. Add one item using the template below.
2. Keep the status as `pending` until development starts.
3. Automation reads pending items before selecting new roadmap work.
4. The implementing PR changes the status to `in_progress` or `resolved` and records evidence.
5. Do not delete resolved feedback; it is part of the audit trail.

Supported statuses: `pending`, `in_progress`, `resolved`, `deferred`.

## Template

```markdown
## FB-001 [pending] Concise problem or request
- PDF: `data/example.pdf`
- Command or notebook cell:
- Expected behavior:
- Actual behavior:
- Error or traceback:
- Acceptance criteria:
```

<!-- Add new feedback items below this line. Increment the identifier. -->
