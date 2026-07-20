# Encrypted PDF benchmark fixture

AKILAN includes a focused generator for a copyright-free encrypted PDF regression input:

```bash
python scripts/generate_encrypted_benchmark_fixtures.py artifacts/encrypted-corpus \
  --evidence artifacts/encrypted-corpus/evidence.json
```

The generator creates `encrypted_user_password.pdf`, a one-page AES-256 encrypted PDF produced entirely through PyMuPDF. It exercises missing-password rejection, invalid-password rejection, successful authentication, and complete artifact publication.

## Public fixture credentials

The passwords in the generator are intentionally public test data:

```text
owner password: akilan-owner
user password:  akilan-user
```

They exist only to make regression tests reproducible. They must never be reused for production documents, examples containing confidential information, or any security-sensitive workflow. The machine-readable evidence deliberately excludes both credential values.

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

After successful authentication, the artifact is published normally and reports that the open document no longer needs a password. Password values are never written into `document.json`, `manifest.json`, page artifacts, cache records, or generated fixture evidence.

## Scope boundary

The general `akilan benchmark` command intentionally does not accept one corpus-wide password. A benchmark corpus can contain documents with different credentials, and accepting a single password would create ambiguous behavior and unnecessary secret exposure. Password-required fixtures are therefore validated through focused generated-fixture tests until a separately reviewed credential-mapping contract is introduced.
