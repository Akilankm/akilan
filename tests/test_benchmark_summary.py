from __future__ import annotations

from akilan.benchmark import ArtifactMetrics, CorpusCaseResult, CorpusReport, PerformanceMetrics
from akilan.benchmark_summary import summarize_corpus_performance


def _metrics(*, pages: int, fingerprint: str) -> ArtifactMetrics:
    return ArtifactMetrics(
        source_sha256="a" * 64,
        page_count=pages,
        text_block_count=1,
        table_count=0,
        image_count=0,
        drawing_count=0,
        link_count=0,
        annotation_count=0,
        widget_count=0,
        reading_order_item_count=1,
        ordered_element_ratio=1.0,
        semantic_role_counts={"paragraph": 1},
        artifact_fingerprint=fingerprint,
    )


def _performance(
    *,
    source: int,
    output: int,
    peak: int,
    cache_hit: bool,
    phases: dict[str, float],
) -> PerformanceMetrics:
    return PerformanceMetrics(
        source_size_bytes=source,
        output_size_bytes=output,
        peak_python_memory_bytes=peak,
        pages_per_second=0.0,
        source_mib_per_second=0.0,
        output_to_source_ratio=0.0,
        cache_hit=cache_hit,
        phase_seconds=phases,
    )


def test_summarize_corpus_performance_is_deterministic_and_auditable() -> None:
    report = CorpusReport(
        cases=[
            CorpusCaseResult(
                source="a.pdf",
                output_dir="a",
                status="passed",
                elapsed_seconds=2.0,
                metrics=_metrics(pages=4, fingerprint="b" * 64),
                performance=_performance(
                    source=1024 * 1024,
                    output=2048,
                    peak=900,
                    cache_hit=False,
                    phases={"extraction": 1.5, "measurement": 0.25},
                ),
            ),
            CorpusCaseResult(
                source="b.pdf",
                output_dir="b",
                status="passed",
                elapsed_seconds=1.0,
                metrics=_metrics(pages=2, fingerprint="c" * 64),
                performance=_performance(
                    source=1024 * 1024,
                    output=4096,
                    peak=500,
                    cache_hit=True,
                    phases={"cache_lookup": 0.1, "measurement": 0.05},
                ),
            ),
            CorpusCaseResult(
                source="missing.pdf",
                output_dir="missing",
                status="failed",
                elapsed_seconds=0.5,
                performance=_performance(
                    source=0,
                    output=0,
                    peak=100,
                    cache_hit=False,
                    phases={"cache_lookup": 0.2},
                ),
                error_type="FileNotFoundError",
                error_message="missing",
            ),
        ]
    )

    summary = summarize_corpus_performance(report)

    assert summary.measured_case_count == 3
    assert summary.cache_hit_count == 1
    assert summary.cache_hit_ratio == 0.333333
    assert summary.total_elapsed_seconds == 3.5
    assert summary.total_source_size_bytes == 2 * 1024 * 1024
    assert summary.total_output_size_bytes == 6144
    assert summary.total_page_count == 6
    assert summary.pages_per_second == 1.714286
    assert summary.source_mib_per_second == 0.571429
    assert summary.peak_python_memory_bytes == 900
    assert summary.phase_seconds == {
        "cache_lookup": 0.3,
        "extraction": 1.5,
        "measurement": 0.3,
    }
    assert summary.to_dict() == summarize_corpus_performance(report).to_dict()


def test_summarize_corpus_performance_handles_empty_report() -> None:
    summary = summarize_corpus_performance(CorpusReport())

    assert summary.measured_case_count == 0
    assert summary.cache_hit_ratio == 0.0
    assert summary.pages_per_second == 0.0
    assert summary.source_mib_per_second == 0.0
    assert summary.peak_python_memory_bytes == 0
    assert summary.phase_seconds == {}
