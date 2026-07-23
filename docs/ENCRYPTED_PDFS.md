# Encrypted PDF handling

AKILAN authenticates encrypted PDFs through PyMuPDF before loading pages or publishing any artifact output. Missing or invalid credentials raise `PDFExtractionError`, and atomic publication preserves the previous known-good artifact.

## Python API

```python
from akilan import PDFArtifactBuilder

artifact = PDFArtifactBuilder().build(
    "encrypted.pdf",
    "artifacts/encrypted",
    password="secret",
)
```

The Python API receives the password in process memory only. Applications remain responsible for sourcing it from an appropriate secret manager.

## CLI password sources

For interactive shell and automation use, prefer a source that does not expose the credential in shell history or process listings.

### Standard input

```bash
printf '%s\n' "$PDF_PASSWORD" | \
  akilan extract encrypted.pdf \
    --output artifacts/encrypted \
    --password-stdin
```

AKILAN reads exactly one line and removes one terminal `LF`, `CR`, or `CRLF` sequence. Leading and trailing spaces in the password are preserved.

### UTF-8 password file

```bash
akilan extract encrypted.pdf \
  --output artifacts/encrypted \
  --password-file /run/secrets/pdf_password
```

The file must be readable, non-empty, and UTF-8 encoded. Protect it with operating-system permissions and delete temporary secret files after use.

### Direct argument

```bash
akilan extract encrypted.pdf \
  --output artifacts/encrypted \
  --password 'secret'
```

This compatibility option can expose the password through shell history and process inspection. It should not be used in production automation.

The three password options are mutually exclusive. Empty standard input, empty files, unreadable files, and invalid PDF credentials fail before artifact publication.

## Operational guarantees

- PyMuPDF remains the only runtime dependency.
- Credentials are never written into `manifest.json`, `document.json`, logs, or benchmark reports.
- Authentication occurs before page extraction.
- Failed authentication cannot replace an existing artifact directory.
- No password prompting occurs, so headless jobs fail deterministically instead of hanging.
