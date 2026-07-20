from __future__ import annotations

import runpy
from pathlib import Path

import pymupdf


def _generate_corpus(output_dir: Path) -> dict[str, object]:
    module = runpy.run_path("scripts/generate_ci_benchmark_corpus.py")
    return module["generate_corpus"](output_dir)


def test_generated_corpus_includes_rotated_cropped_geometry(tmp_path: Path) -> None:
    payload = _generate_corpus(tmp_path / "corpus")

    assert payload["case_count"] == 6
    cases = {case["case_id"]: case for case in payload["cases"]}
    assert sorted(cases) == [
        "annotated_form",
        "image_heavy",
        "mixed_layout",
        "rotated_cropped",
        "single_column",
        "table_heavy",
    ]

    rotated_case = cases["rotated_cropped"]
    assert rotated_case["page_count"] == 1
    assert rotated_case["size_bytes"] > 0
    assert rotated_case["pages"][0]["rotation"] == 90
    assert rotated_case["pages"][0]["crop_box"] != rotated_case["pages"][0]["media_box"]

    with pymupdf.open(rotated_case["path"]) as document:
        page = document[0]
        assert page.rotation == 90
        assert page.cropbox != page.mediabox
        text = page.get_text()
        assert "Rotated and Cropped" in text
        assert "media-box, crop-box, and rotation evidence" in text


def test_generated_geometry_evidence_is_stably_ordered(tmp_path: Path) -> None:
    payload = _generate_corpus(tmp_path / "corpus")

    case_ids = [case["case_id"] for case in payload["cases"]]
    assert case_ids == sorted(case_ids)
    for case in payload["cases"]:
        assert [page["page_number"] for page in case["pages"]] == list(
            range(1, case["page_count"] + 1)
        )
