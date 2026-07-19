"""Operational build-performance evidence outside the canonical artifact schema."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

from .models import DocumentArtifact, PageArtifact
from .serialization import dump_json

BUILD_PROFILE_FILE = ".akilan-profile.json"
BUILD_PROFILE_VERSION = "1"


@dataclass
class BuildProfiler:
    """Collect monotonic timing and element-count evidence for one artifact build."""

    started_at: float = field(default_factory=perf_counter)
    phase_seconds: dict[str, float] = field(default_factory=dict)
    pages: list[dict[str, Any]] = field(default_factory=list)

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        """Measure one named phase and accumulate repeated invocations."""

        started = perf_counter()
        try:
            yield
        finally:
            elapsed = max(0.0, perf_counter() - started)
            self.phase_seconds[name] = self.phase_seconds.get(name, 0.0) + elapsed

    def record_page(self, page: PageArtifact, elapsed_seconds: float) -> None:
        """Record stable per-page throughput inputs after extraction completes."""

        self.pages.append(
            {
                "page_index": page.page_index,
                "page_number": page.page_number,
                "elapsed_ms": _milliseconds(elapsed_seconds),
                "element_counts": {
                    "text_blocks": len(page.text_blocks),
                    "tables": len(page.tables),
                    "images": len(page.images),
                    "drawings": len(page.drawings),
                    "links": len(page.links),
                    "annotations": len(page.annotations),
                    "widgets": len(page.widgets),
                },
            }
        )

    def to_dict(self, artifact: DocumentArtifact) -> dict[str, Any]:
        """Return a compact JSON-safe operational profile."""

        total_seconds = max(0.0, perf_counter() - self.started_at)
        pages = sorted(self.pages, key=lambda item: (item["page_index"], item["page_number"]))
        extracted_pages = len(pages)
        return {
            "profile_version": BUILD_PROFILE_VERSION,
            "source_sha256": artifact.source.get("sha256"),
            "schema_version": artifact.schema_version,
            "generator": artifact.generator,
            "total_elapsed_ms": _milliseconds(total_seconds),
            "throughput_pages_per_second": round(extracted_pages / total_seconds, 6)
            if total_seconds > 0
            else None,
            "phase_elapsed_ms": {
                name: _milliseconds(seconds)
                for name, seconds in sorted(self.phase_seconds.items())
            },
            "pages": pages,
            "statistics": artifact.statistics,
        }


def write_build_profile(
    destination: str | Path,
    profiler: BuildProfiler,
    artifact: DocumentArtifact,
) -> Path:
    """Write the profile into the staged artifact directory before publication."""

    path = Path(destination) / BUILD_PROFILE_FILE
    dump_json(path, profiler.to_dict(artifact))
    return path


def _milliseconds(seconds: float) -> float:
    return round(max(0.0, seconds) * 1000.0, 3)
