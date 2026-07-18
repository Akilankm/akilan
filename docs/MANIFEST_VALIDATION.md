# Manifest integrity validation

AKILAN exposes a dependency-free validator for persisted `manifest.json` files:

```python
import json
from pathlib import Path

from akilan import validate_manifest

manifest = json.loads(Path("artifacts/document/manifest.json").read_text(encoding="utf-8"))
validate_manifest(manifest)
```

The validator checks the stable manifest envelope, page summaries, artifact-file indexes, non-empty paths, and duplicate page numbers. It aggregates violations with JSON-style paths so CI and downstream ingestion systems can report all repair actions in one pass.

Use `raise_on_error=False` to obtain a list of `SchemaViolation` objects instead of raising `ArtifactSchemaError`.

This validator is additive and does not change the canonical document artifact schema. It validates persisted index integrity without checking filesystem existence; callers that require physical-file attestation should separately resolve every declared path beneath the trusted artifact root.
