# PDF preflight diagnostics

AKILAN provides a read-only source inspection boundary for classifying PDF failures before artifact construction:

```python
from akilan.pdf_preflight import preflight_pdf

report = preflight_pdf("data/complex.pdf", password=None)

if not report.accepted:
    print(report.to_dict())
```

## Stable statuses

| Status | Meaning |
|---|---|
| `ready` | The source is a readable PDF with at least one page. |
| `missing` | The source path does not exist. |
| `not_a_file` | The source path exists but is not a regular file. |
| `empty_file` | The file contains zero bytes. |
| `unreadable_pdf` | PyMuPDF or the operating system cannot open the source. |
| `not_pdf` | The opened document is not a PDF. |
| `password_required` | The PDF requires a password and none was supplied. |
| `invalid_password` | The supplied password did not authenticate. |
| `zero_pages` | The PDF is structurally readable but contains no pages. |

## Evidence contract

The immutable report includes normalized source path, byte size, page count when available, PDF/encryption/password/repair flags, and sanitized exception classification. Password values are never retained in report evidence.

A repaired PDF is not rejected solely because PyMuPDF repaired it. `is_repaired` is preserved as evidence so an enterprise caller can enforce a stricter policy without losing the observable recovery state.

## Safety properties

Preflight is deliberately non-mutating. It does not:

- build or publish an artifact;
- write cache metadata;
- repair or rewrite the input;
- create temporary output directories;
- weaken the builder's atomic publication boundary.

PyMuPDF remains the only runtime dependency.
