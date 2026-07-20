from __future__ import annotations

import runpy
from pathlib import Path

import pymupdf


def _generate_corpus(output_dir: Path) -> dict[str, object]:
    module = runpy.run_path("scripts/generate_ci_benchmark_corpus.py")
    return module["generate_corpus"](output_dir)


def test_generated_table_fixture_preserves_native_table_structure(tmp_path: Path) -> None:
    payload = _generate_corpus(tmp_path / "corpus")
    cases = {case["case_id"]: case for case in payload["cases"]}

    table_case = cases["table_heavy"]
    assert table_case["page_count"] == 1
    assert table_case["pages"][0]["table_count"] >= 1

    with pymupdf.open(table_case["path"]) as document:
        page = document[0]
        tables = page.find_tables().tables
        assert len(tables) >= 1
        extracted = tables[0].extract()
        flattened = [value for row in extracted for value in row if value]
        assert "Quarterly Quality Evidence" in flattened
        assert "Coverage" in flattened
        assert "Pass" in flattened


def test_plain_fixtures_report_no_native_tables(tmp_path: Path) -> None:
    payload = _generate_corpus(tmp_path / "corpus")
    cases = {case["case_id"]: case for case in payload["cases"]}

    for case_id in ("annotated_form", "rotated_cropped", "single_column"):
        assert cases[case_id]["pages"][0]["table_count"] == 0
