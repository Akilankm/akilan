"""Deterministic benchmark metrics for AKILAN document artifacts."""

from __future__ import annotations

import hashlib
import json
import tracemalloc
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from .benchmark_cache_validation import validate_benchmark_cache_entry
from .builder import PDFArtifactBuilder
from .config import ExtractionConfig
from .models import DocumentArtifact
from .serialization import to_jsonable

_MIB = 1024 * 1024
_CACHE_FILENAME = ".akilan-benchmark-cache.json"
_CACHE_FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class ArtifactMetrics:
    """Stable quality and coverage metrics for one extracted artifact."""

    source_sha256: str
    page_count: int
    text_block_count: int
    table_count: int
    image_count: int
    drawing_count: int
    link_count: int
    annotation_count: int
    widget_count: int
    reading_order_item_count: int
    ordered_element_ratio: float
    semantic_role_counts: dict[str, int]
    artifact_fingerprint: str


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Process-local performance evidence for one extraction case."""

    source_size_bytes: int
    output_size_bytes: int
    peak_python_memory_bytes: int
    pages_per_second: float
    source_mib_per_second: float
    output_to_source_ratio: float
    cache_hit: bool = False
    phase_seconds: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CorpusCaseResult:
    """Outcome of extracting and measuring one corpus PDF."""

    source: str
    output_dir: str
    status: Literal["passed", "failed"]
    elapsed_seconds: float
    metrics: ArtifactMetrics | None = None
    performance: PerformanceMetrics | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class CorpusReport:
    """Machine-readable report for a benchmark corpus run."""

    cases: list[CorpusCaseResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(case.status == "passed" for case in self.cases)

    @property
    def failed(self) -> int:
        return sum(case.status == "failed" for case in self.cases)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "total": len(self.cases),
                "succeeded": self.succeeded,
                "failed": self.failed,
            },
            "cases": to_jsonable(self.cases),
        }


def artifact_fingerprint(artifact: DocumentArtifact) -> str:
    """Return a canonical SHA-256 fingerprint of artifact content."""

    payload = json.dumps(
        artifact.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def measure_artifact(artifact: DocumentArtifact) -> ArtifactMetrics:
    """Compute deterministic coverage metrics from a document artifact."""

    pages = artifact.pages
    text_blocks = [block for page in pages for block in page.text_blocks]
    readable_elements = sum(
        len(page.text_blocks) + len(page.tables) + len(page.images) + len(page.drawings)
        for page in pages
    )
    ordered_elements = sum(len(page.reading_order) for page in pages)
    role_counts: dict[str, int] = {}
    for block in text_blocks:
        role_counts[block.semantic_role] = role_counts.get(block.semantic_role, 0) + 1

    return ArtifactMetrics(
        source_sha256=str(artifact.source.get("sha256", "")),
        page_count=len(pages),
        text_block_count=len(text_blocks),
        table_count=sum(len(page.tables) for page in pages),
        image_count=sum(len(page.images) for page in pages),
        drawing_count=sum(len(page.drawings) for page in pages),
        link_count=sum(len(page.links) for page in pages),
        annotation_count=sum(len(page.annotations) for page in pages),
        widget_count=sum(len(page.widgets) for page in pages),
        reading_order_item_count=ordered_elements,
        ordered_element_ratio=round(ordered_elements / readable_elements, 6) if readable_elements else 1.0,
        semantic_role_counts=dict(sorted(role_counts.items())),
        artifact_fingerprint=artifact_fingerprint(artifact),
    )


def _case_directory(source: Path) -> str:
    identity = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:12]
    return f"{source.stem}-{identity}"


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(entry.stat().st_size for entry in path.rglob("*") if entry.is_file())


def _normalized_phases(phases: dict[str, float] | None) -> dict[str, float]:
    return {name: round(max(0.0, duration), 6) for name, duration in sorted((phases or {}).items())}


def _performance_metrics(
    *,
    source: Path,
    destination: Path,
    elapsed_seconds: float,
    peak_python_memory_bytes: int,
    page_count: int,
    cache_hit: bool = False,
    phase_seconds: dict[str, float] | None = None,
) -> PerformanceMetrics:
    source_size = source.stat().st_size if source.is_file() else 0
    output_size = _directory_size(destination)
    safe_elapsed = max(elapsed_seconds, 1e-9)
    return PerformanceMetrics(
        source_size_bytes=source_size,
        output_size_bytes=output_size,
        peak_python_memory_bytes=peak_python_memory_bytes,
        pages_per_second=round(page_count / safe_elapsed, 6),
        source_mib_per_second=round((source_size / _MIB) / safe_elapsed, 6),
        output_to_source_ratio=round(output_size / source_size, 6) if source_size else 0.0,
        cache_hit=cache_hit,
        phase_seconds=_normalized_phases(phase_seconds),
    )


def _memory_peak_delta(baseline_bytes: int) -> int:
    _, peak_bytes = tracemalloc.get_traced_memory()
    return max(0, peak_bytes - baseline_bytes)


def _source_sha256(source: Path) -> str:
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version() -> str:
    try:
        return version("akilan")
    except PackageNotFoundError:
        return "0+unknown"


def _cache_identity(source: Path, config: ExtractionConfig) -> str:
    payload = {
        "cache_format_version": _CACHE_FORMAT_VERSION,
        "package_version": _package_version(),
        "source_sha256": _source_sha256(source),
        "config": asdict(config),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_cached_metrics(destination: Path, identity: str) -> ArtifactMetrics | None:
    if validate_benchmark_cache_entry(destination, expected_identity=identity):
        return None

    marker = destination / _CACHE_FILENAME
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
        if payload.get("cache_format_version") != _CACHE_FORMAT_VERSION:
            return None
        return ArtifactMetrics(**payload["metrics"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _write_cache_marker(destination: Path, identity: str, metrics: ArtifactMetrics) -> None:
    marker = destination / _CACHE_FILENAME
    payload = {
        "cache_format_version": _CACHE_FORMAT_VERSION,
        "identity": identity,
        "metrics": asdict(metrics),
    }
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(marker)


def run_corpus(
    pdf_paths: Iterable[str | Path],
    output_root: str | Path,
    *,
    config: ExtractionConfig | None = None,
    use_cache: bool = True,
) -> CorpusReport:
    """Extract a corpus independently and return auditable per-file outcomes.

    Successful cases are reused only when the source bytes, complete extraction
    configuration, installed package version, cache format, marker metrics, and
    persisted artifact directory all agree. Invalid cache state is treated as a
    miss and rebuilt through the normal extraction path.
    """

    root = Path(output_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    effective_config = config or ExtractionConfig(overwrite=True)
    cases: list[CorpusCaseResult] = []

    for source_value in sorted((Path(path).expanduser().resolve() for path in pdf_paths), key=str):
        destination = root / _case_directory(source_value)
        started = perf_counter()
        phases: dict[str, float] = {}
        cache_started = perf_counter()
        try:
            identity = _cache_identity(source_value, effective_config)
            cached_metrics = _read_cached_metrics(destination, identity) if use_cache else None
            phases["cache_lookup"] = perf_counter() - cache_started
            if cached_metrics is not None:
                elapsed = round(perf_counter() - started, 6)
                phases["total"] = elapsed
                cases.append(
                    CorpusCaseResult(
                        source=str(source_value),
                        output_dir=str(destination),
                        status="passed",
                        elapsed_seconds=elapsed,
                        metrics=cached_metrics,
                        performance=_performance_metrics(
                            source=source_value,
                            destination=destination,
                            elapsed_seconds=elapsed,
                            peak_python_memory_bytes=0,
                            page_count=cached_metrics.page_count,
                            cache_hit=True,
                            phase_seconds=phases,
                        ),
                    )
                )
                continue
        except (OSError, ValueError):
            phases["cache_lookup"] = perf_counter() - cache_started
            identity = ""

        owns_tracemalloc = not tracemalloc.is_tracing()
        if owns_tracemalloc:
            tracemalloc.start()
            memory_baseline = 0
        else:
            memory_baseline, _ = tracemalloc.get_traced_memory()
        try:
            extraction_started = perf_counter()
            artifact = PDFArtifactBuilder(effective_config).build(source_value, destination)
            phases["extraction"] = perf_counter() - extraction_started

            measurement_started = perf_counter()
            artifact_metrics = measure_artifact(artifact)
            phases["measurement"] = perf_counter() - measurement_started

            if use_cache and identity:
                cache_write_started = perf_counter()
                _write_cache_marker(destination, identity, artifact_metrics)
                phases["cache_write"] = perf_counter() - cache_write_started

            elapsed = round(perf_counter() - started, 6)
            phases["total"] = elapsed
            peak_memory = _memory_peak_delta(memory_baseline)
            cases.append(
                CorpusCaseResult(
                    source=str(source_value),
                    output_dir=str(destination),
                    status="passed",
                    elapsed_seconds=elapsed,
                    metrics=artifact_metrics,
                    performance=_performance_metrics(
                        source=source_value,
                        destination=destination,
                        elapsed_seconds=elapsed,
                        peak_python_memory_bytes=peak_memory,
                        page_count=artifact_metrics.page_count,
                        phase_seconds=phases,
                    ),
                )
            )
        except Exception as exc:
            elapsed = round(perf_counter() - started, 6)
            phases.setdefault("extraction", max(0.0, elapsed - sum(phases.values())))
            phases["total"] = elapsed
            peak_memory = _memory_peak_delta(memory_baseline)
            cases.append(
                CorpusCaseResult(
                    source=str(source_value),
                    output_dir=str(destination),
                    status="failed",
                    elapsed_seconds=elapsed,
                    performance=_performance_metrics(
                        source=source_value,
                        destination=destination,
                        elapsed_seconds=elapsed,
                        peak_python_memory_bytes=peak_memory,
                        page_count=0,
                        phase_seconds=phases,
                    ),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
        finally:
            if owns_tracemalloc:
                tracemalloc.stop()

    return CorpusReport(cases=cases)


def write_corpus_report(report: CorpusReport, destination: str | Path) -> Path:
    """Persist a machine-readable JSON report and return its resolved path."""

    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
