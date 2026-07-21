# PDF preflight CLI

AKILAN exposes deterministic, read-only source diagnostics through the installed `akilan-preflight` command.

```bash
akilan-preflight data/complex.pdf \
  --report artifacts/preflight/complex.json
```

The command exits with `0` only when the source is ready for artifact construction. Rejected inputs exit with `1` and write the diagnostic payload to standard error, which makes the command suitable as a CI or shell gate before `akilan extract`.

## Encrypted PDFs

Passwords may be supplied from exactly one source:

```bash
akilan-preflight data/encrypted.pdf --password-file .secrets/pdf-password.txt
printf '%s\n' "$PDF_PASSWORD" | akilan-preflight data/encrypted.pdf --password-stdin
```

Using `--password` is supported but exposes the value to process listings and shell history. Password values are never included in the emitted JSON evidence.

## Output contract

The JSON payload includes the normalized source path, size, page count when available, PDF/encryption/password/repair state, the stable preflight status, and an `accepted` boolean. When `--report` is provided, the underlying deterministic preflight report is written atomically through the shared report writer.

Passing evidence is written to standard output. Rejected evidence is written to standard error. The command never creates an artifact directory, cache entry, repair output, or modified PDF.

## Statuses

The command preserves the API statuses:

- `ready`
- `missing`
- `not_a_file`
- `empty_file`
- `unreadable_pdf`
- `not_pdf`
- `password_required`
- `invalid_password`
- `zero_pages`

Repaired PDFs remain observable through `is_repaired`; they are not rejected solely because PyMuPDF repaired them.
