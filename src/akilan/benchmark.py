"""Deterministic benchmark metrics for AKILAN document artifacts."""

from __future__ import annotations

import hashlib
import json
import tracemalloc
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from .builder import PDFArtifactBuilder
from .config import ExtractionConfig
from .models import DocumentArtifact
from .serialization import to_jsonable

_MIB = 1024 * 1024


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


def _performance_metrics(
    *,
    source: Path,
    destination: Path,
    elapsed_seconds: float,
    peak_python_memory_bytes: int,
    page_count: int,
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
    )


def _memory_peak_delta(baseline_bytes: int) -> int:
    _, peak_bytes = tracemalloc.get_traced_memory()
    return max(0, peak_bytes - baseline_bytes)


def run_corpus(
    pdf_paths: Iterable[str | Path],
    output_root: str | Path,
    *,
    config: ExtractionConfig | None = None,
) -> CorpusReport:
    """Extract a corpus independently and return auditable per-file outcomes."""

    root = Path(output_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    effective_config = config or ExtractionConfig(overwrite=True)
    cases: list[CorpusCaseResult] = []

    for source_value in sorted((Path(path).expanduser().resolve() for path in pdf_paths), key=str):
        destination = root / _case_directory(source_value)
        started = perf_counter()
        owns_tracemalloc = not tracemalloc.is_tracing()
        if owns_tracemalloc:
            tracemalloc.start()
            memory_baseline = 0
        else:
            memory_baseline, _ = tracemalloc.get_traced_memory()
        try:
            artifact = PDFArtifactBuilder(effective_config).build(source_value, destination)
            elapsed = round(perf_counter() - started, 6)
            peak_memory = _memory_peak_delta(memory_baseline)
            artifact_metrics = measure_artifact(artifact)
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
                    ),
                )
            )
        except Exception as exc:
            elapsed = round(perf_counter() - started, 6)
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
