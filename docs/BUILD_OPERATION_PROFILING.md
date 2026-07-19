# Cache-aware build operation profiling

`build_or_resolve_artifact()` returns operational timing and output-volume evidence through `ArtifactBuildResolution.profile`.

```python
from akilan import build_or_resolve_artifact

result = build_or_resolve_artifact("data/public/complex.pdf", "artifacts/complex")
print(result.profile.to_dict())
```

The profile reports:

- cache lookup duration;
- artifact build duration when extraction was required;
- post-build validation and loading duration;
- end-to-end elapsed duration;
- extracted page count;
- deterministic document element counts copied from canonical artifact statistics.

On a validated cache hit, `artifact_build_ms` and `postbuild_validation_ms` are exactly `0.0`, making avoided work explicit. On a miss, all three orchestration phases are measured with a monotonic clock.

## Contract boundary

Performance measurements are operational evidence, not canonical PDF evidence. They are therefore returned by the orchestration API and excluded from `document.json`, `manifest.json`, page JSON, cache identity, and artifact-schema validation. This prevents machine-dependent timing values from affecting artifact equivalence or cache reuse.

Durations are rounded to milliseconds and must be treated as observations, not deterministic golden values. Tests assert structure, non-negativity, phase presence, and output counts rather than exact timing.

## Interpretation

Use `artifact_build_ms` to compare extraction configurations or PDF classes. Use `element_counts` and `page_count` to normalize work volume. The ratio between build time and page or element volume provides a first diagnostic signal before introducing lower-level instrumentation.

This slice does not claim peak-memory measurement or per-page extraction timing. Those remain follow-up work under issue #7.
