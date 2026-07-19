# AKILAN User Feedback Queue

Use this file to record errors, feature requests, validation observations, and enterprise requirements discovered while testing the latest merged development branch.

## Workflow

1. Add one item using the template below.
2. Keep the status as `pending` until development starts.
3. Automation reads pending items before selecting new roadmap work.
4. The implementing PR changes the status to `in_progress` or `resolved` and records evidence.
5. Do not delete resolved feedback; it is part of the audit trail.

Supported statuses: `pending`, `in_progress`, `resolved`, `deferred`.

## Integrity rules

- Every item identifier must use `FB-` followed by at least three digits, for example `FB-001`.
- Identifiers are permanent and must never be reused, including after an item is resolved or deferred.
- Every item requires a non-empty title after its status token.
- Malformed headings, unsupported statuses, duplicate identifiers, and missing titles fail fast with a source line number.

These constraints prevent an automated development cycle from silently skipping, duplicating, or ambiguously resolving user feedback.

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
