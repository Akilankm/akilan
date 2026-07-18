# Offline Corpus Verification

`verify_corpus()` audits every PDF declared in `data/sources.json` without using the network.

```python
from akilan import verify_corpus

results = verify_corpus("data/sources.json", "data")
for result in results:
    print(result.source_id, result.status, result.actual_sha256)

if not all(result.valid for result in results):
    raise SystemExit("Corpus integrity verification failed")
```

## Statuses

- `valid`: the file is present, opens as a non-empty PDF through PyMuPDF, and matches its declared SHA-256 when pinned.
- `missing`: the declared destination does not exist as a regular file.
- `invalid_pdf`: the local file cannot be opened as a non-empty PDF.
- `checksum_mismatch`: the PDF is structurally readable but its bytes differ from the reviewed manifest pin.

The function returns one result per manifest entry and does not stop at the first bad file. This makes notebook, CI, and benchmark reports complete and auditable. It never downloads, repairs, removes, or replaces files.

Run `sync_corpus()` separately when acquisition or repair is intentionally required. Verification should run before golden benchmarks so unexpected local drift cannot be mistaken for an extraction regression.
