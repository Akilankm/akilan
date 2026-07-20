# Encrypted PDF benchmark fixtures

AKILAN includes a focused generator for copyright-free encrypted PDF regression inputs:

```bash
python scripts/generate_encrypted_benchmark_fixtures.py artifacts/encrypted-corpus \
  --evidence artifacts/encrypted-corpus/evidence.json
```

The generator creates two one-page AES-256 encrypted PDFs entirely through PyMuPDF:

| Case | Purpose | Expected open behavior |
|---|---|---|
| `encrypted_owner_only.pdf` | Proves that encryption metadata can be preserved when no user password is required | Opens without authentication while remaining encrypted |
| `encrypted_user_password.pdf` | Exercises missing-password rejection, invalid-password rejection, and successful authenticated extraction | Requires the public fixture user password |

## Public fixture credentials

The passwords in the generator are intentionally public test data:

```text
owner password: akilan-owner
user password:  akilan-user
```

They exist only to make regression tests reproducible. They must never be reused for production documents, examples containing confidential information, or any security-sensitive workflow.

## Extraction contract

`PDFArtifactBuilder.build()` behaves fail-closed for a PDF that requires authentication:

```python
from akilan import ExtractionConfig, PDFArtifactBuilder

artifact = PDFArtifactBuilder(
    ExtractionConfig(overwrite=True)
).build(
    "artifacts/encrypted-corpus/encrypted_user_password.pdf",
    "artifacts/encrypted-output",
    password="akilan-user",
)
```

When the password is absent or invalid:

- `PDFExtractionError` is raised before page extraction;
- the staging directory is removed;
- no partial destination artifact is published.

After successful authentication, the canonical artifact records that the source PDF is encrypted while reporting that the open document no longer needs a password. Password values are never written into `document.json`, `manifest.json`, page artifacts, cache records, or benchmark evidence.

## Scope boundary

The general `akilan benchmark` command intentionally does not accept corpus-wide passwords. A benchmark corpus can contain documents with different credentials, and accepting a single password would create ambiguous behavior and unnecessary secret exposure. Password-required fixtures are therefore validated through focused generated-fixture tests until a separately reviewed credential-mapping contract is introduced.
