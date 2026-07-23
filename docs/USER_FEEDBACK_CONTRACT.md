# User feedback validation contract

`user_feedback.md` is the persistent intake queue for errors, feature requests, and enterprise validation observations. Future development cycles depend on its headings being machine-readable, so malformed feedback must fail closed rather than be silently skipped.

Validate the queue with only the Python standard library:

```bash
python scripts/validate_user_feedback.py user_feedback.md \
  --report artifacts/user-feedback-contract.json
```

A feedback item heading must use this exact shape:

```markdown
## FB-001 [pending] Concise problem or request
```

The validator enforces:

- identifiers use `FB-` followed by at least three digits;
- identifiers are unique and use canonical zero padding;
- status is one of `pending`, `in_progress`, `resolved`, or `deferred`;
- titles are non-empty;
- examples inside fenced Markdown blocks are ignored;
- every failure identifies the source line;
- successful evidence reports all normalized items and status counts.

CI persists `artifacts/user-feedback-contract.json` with the existing engineering evidence bundle. The validator never edits, resolves, reorders, or deletes feedback items.
