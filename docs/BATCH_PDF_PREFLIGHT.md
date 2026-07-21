# Batch PDF preflight

AKILAN can inspect a complete PDF corpus before extraction without creating artifacts or modifying source files.

```python
from akilan.pdf_preflight_batch import preflight_pdf_batch

report = preflight_pdf_batch("data", recursive=True)
if not report.accepted:
    for entry in report.entries:
        if not entry.accepted:
            print(entry.source_path, entry.status)
```

The report is deterministic: discovered PDFs are ordered by normalized path, status counts are key-sorted, and a canonical SHA-256 fingerprint covers the root, recursion policy, entry evidence, and status summary.

An empty directory fails closed. A corpus is accepted only when at least one PDF is discovered and every source is `ready`.

Encrypted sources may be supplied through an in-memory password mapping keyed by normalized absolute path or root-relative POSIX path. Password values are used only for authentication and are never stored in the batch report or fingerprint evidence.

The API remains read-only and uses the existing single-file `preflight_pdf()` boundary, so source statuses and diagnostics stay consistent across individual and corpus workflows. PyMuPDF remains the only runtime dependency.
