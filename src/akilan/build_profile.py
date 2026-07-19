"""Operational performance evidence outside the canonical artifact schema."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any


@dataclass(frozen=True, slots=True)
class ArtifactOperationProfile:
    """Timing and output-volume evidence for one cache-aware build request."""

    cache_lookup_ms: float
    artifact_build_ms: float
    postbuild_validation_ms: float
    total_elapsed_ms: float
    page_count: int
    element_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Return stable JSON-safe operational evidence."""

        return {
            "cache_lookup_ms": self.cache_lookup_ms,
            "artifact_build_ms": self.artifact_build_ms,
            "postbuild_validation_ms": self.postbuild_validation_ms,
            "total_elapsed_ms": self.total_elapsed_ms,
            "page_count": self.page_count,
            "element_counts": dict(sorted(self.element_counts.items())),
        }


class OperationProfiler:
    """Accumulate monotonic phase timings for one orchestration call."""

    def __init__(self) -> None:
        self._started_at = perf_counter()
        self._phase_started_at: float | None = None
        self._phase_ms: dict[str, float] = {}

    def start(self) -> None:
        self._phase_started_at = perf_counter()

    def stop(self, name: str) -> None:
        if self._phase_started_at is None:
            raise RuntimeError("operation profile phase was not started")
        self._phase_ms[name] = _milliseconds(perf_counter() - self._phase_started_at)
        self._phase_started_at = None

    def finish(self, artifact: dict[str, Any]) -> ArtifactOperationProfile:
        statistics = artifact.get("statistics")
        counts = statistics if isinstance(statistics, dict) else {}
        document = artifact.get("document")
        metadata = document if isinstance(document, dict) else {}
        return ArtifactOperationProfile(
            cache_lookup_ms=self._phase_ms.get("cache_lookup", 0.0),
            artifact_build_ms=self._phase_ms.get("artifact_build", 0.0),
            postbuild_validation_ms=self._phase_ms.get("postbuild_validation", 0.0),
            total_elapsed_ms=_milliseconds(perf_counter() - self._started_at),
            page_count=_nonnegative_int(metadata.get("extracted_page_count")),
            element_counts={
                str(name): _nonnegative_int(value)
                for name, value in counts.items()
                if isinstance(name, str) and isinstance(value, int) and not isinstance(value, bool)
            },
        )


def _milliseconds(seconds: float) -> float:
    return round(max(0.0, seconds) * 1000.0, 3)


def _nonnegative_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0
