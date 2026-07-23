# Performance execution identity

Performance baselines are meaningful only when the current run and approved baseline were produced under the same execution context. Aggregate counters and source fingerprints do not capture runtime or extraction-configuration drift.

`build_performance_execution_identity()` creates deterministic evidence binding a run to:

- Python implementation and version;
- operating-system family and machine architecture;
- PyMuPDF version;
- AKILAN package version;
- the complete validated `ExtractionConfig`.

```python
from akilan.config import ExtractionConfig
from akilan.performance_execution_identity import (
    assess_performance_execution_identity_match,
    build_performance_execution_identity,
)

identity = build_performance_execution_identity(
    ExtractionConfig(render_pages=True, render_dpi=144),
)

if not assess_performance_execution_identity_match(approved, identity):
    raise RuntimeError("performance execution context differs from the approved baseline")
```

The lowercase SHA-256 fingerprint is calculated through AKILAN's canonical JSON contract. Mapping insertion order and formatting therefore do not affect identity.

Hostnames, process identifiers, timestamps, and other volatile values are deliberately excluded. Hardware model, CPU governor, container limits, and background system load are not inferred; production baseline governance should record those externally when they materially affect the benchmark.

This boundary is additive and read-only. It does not alter benchmark reports, canonical artifacts, cache keys, or the artifact schema.
