from __future__ import annotations

import runpy
from pathlib import Path

import pymupdf


def _generate_corpus(output_dir: Path) -> dict[str, object]:
    module = runpy.run_path("scripts/generate_ci_benchmark_corpus.py")
    return module["generate_corpus"](output_dir)


def test_generated_corpus_preserves_annotation_and_widget_evidence(tmp_path: Path) -> None:
    payload = _generate_corpus(tmp_path / "corpus")
    cases = {case["case_id"]: case for case in payload["cases"]}

    annotated_case = cases["annotated_form"]
    assert annotated_case["page_count"] == 1
    assert annotated_case["pages"][0]["annotation_count"] == 1
    assert annotated_case["pages"][0]["widget_count"] == 1

    with pymupdf.open(annotated_case["path"]) as document:
        page = document[0]
        annotations = list(page.annots() or ())
        widgets = list(page.widgets() or ())

        assert len(annotations) == 1
        assert annotations[0].info["content"] == (
            "Generated review note for deterministic annotation extraction."
        )
        assert len(widgets) == 1
        assert widgets[0].field_name == "reviewer_name"
        assert widgets[0].field_value == "AKILAN"
        assert widgets[0].field_type == pymupdf.PDF_WIDGET_TYPE_TEXT


def test_page_evidence_reports_zero_counts_for_plain_cases(tmp_path: Path) -> None:
    payload = _generate_corpus(tmp_path / "corpus")
    cases = {case["case_id"]: case for case in payload["cases"]}

    for case_id in ("mixed_layout", "rotated_cropped", "single_column"):
        page_evidence = cases[case_id]["pages"][0]
        assert page_evidence["annotation_count"] == 0
        assert page_evidence["widget_count"] == 0
