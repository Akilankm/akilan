"""Deterministic benchmark metrics for AKILAN document artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from .builder import PDFArtifactBuilder
from .config import ExtractionConfig
from .models import DocumentArtifact
from .serialization import to_jsonable


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
class CorpusCaseResult:
    """Outcome of extracting and measuring one corpus PDF."""

    source: str
    output_dir: str
    status: Literal["passed", "failed"]
    elapsed_seconds: float
    metrics: ArtifactMetrics | None = None
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
        try:
            artifact = PDFArtifactBuilder(effective_config).build(source_value, destination)
            cases.append(
                CorpusCaseResult(
                    source=str(source_value),
                    output_dir=str(destination),
                    status="passed",
                    elapsed_seconds=round(perf_counter() - started, 6),
                    metrics=measure_artifact(artifact),
                )
            )
        except Exception as exc:
            cases.append(
                CorpusCaseResult(
                    source=str(source_value),
                    output_dir=str(destination),
                    status="failed",
                    elapsed_seconds=round(perf_counter() - started, 6),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )

    return CorpusReport(cases=cases)


def write_corpus_report(report: CorpusReport, destination: str | Path) -> Path:
    """Persist a machine-readable JSON report and return its resolved path."""

    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
