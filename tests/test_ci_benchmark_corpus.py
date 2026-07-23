from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pymupdf

_SCRIPT = Path(__file__).parents[1] / "scripts" / "generate_ci_benchmark_corpus.py"
_SPEC = importlib.util.spec_from_file_location("generate_ci_benchmark_corpus", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_generate_corpus_creates_valid_stable_case_set(tmp_path: Path) -> None:
    output = tmp_path / "corpus"

    payload = _MODULE.generate_corpus(output)

    assert payload["case_count"] == 7
    assert [case["case_id"] for case in payload["cases"]] == [
        "annotated_form",
        "image_heavy",
        "mixed_layout",
        "rotated_cropped",
        "single_column",
        "table_heavy",
        "vector_heavy",
    ]
    assert sorted(path.name for path in output.glob("*.pdf")) == [
        "annotated_form.pdf",
        "image_heavy.pdf",
        "mixed_layout.pdf",
        "rotated_cropped.pdf",
        "single_column.pdf",
        "table_heavy.pdf",
        "vector_heavy.pdf",
    ]
    for case in payload["cases"]:
        path = Path(case["path"])
        assert path.is_file()
        assert case["size_bytes"] == path.stat().st_size
        assert len(case["pages"]) == case["page_count"]
        with pymupdf.open(path) as document:
            assert document.is_pdf
            assert document.page_count == case["page_count"] == 1
            assert document.metadata["author"] == "AKILAN"


def test_image_heavy_fixture_preserves_reuse_and_occurrence_geometry(tmp_path: Path) -> None:
    payload = _MODULE.generate_corpus(tmp_path / "corpus")
    image_case = next(case for case in payload["cases"] if case["case_id"] == "image_heavy")
    page_evidence = image_case["pages"][0]

    assert page_evidence["image_occurrence_count"] == 3
    assert page_evidence["embedded_image_count"] == 2

    with pymupdf.open(image_case["path"]) as document:
        page = document[0]
        image_info = page.get_image_info(xrefs=True)
        assert len(image_info) == 3
        assert image_info[0]["xref"] == image_info[1]["xref"]
        assert image_info[2]["xref"] != image_info[0]["xref"]
        assert image_info[0]["bbox"] != image_info[1]["bbox"]
        assert "Figure A: primary generated image" in page.get_text()
        assert "Figure B: reused image, rotated" in page.get_text()
        assert "Figure C: distinct square image" in page.get_text()


def test_vector_heavy_fixture_preserves_path_and_style_evidence(tmp_path: Path) -> None:
    payload = _MODULE.generate_corpus(tmp_path / "corpus")
    vector_case = next(case for case in payload["cases"] if case["case_id"] == "vector_heavy")
    page_evidence = vector_case["pages"][0]

    assert page_evidence["drawing_count"] == 4
    assert page_evidence["drawing_item_count"] >= 8
    assert page_evidence["image_occurrence_count"] == 0

    with pymupdf.open(vector_case["path"]) as document:
        page = document[0]
        drawings = page.get_drawings()
        assert len(drawings) == 4
        assert any(drawing.get("fill") is not None for drawing in drawings)
        assert any(drawing.get("dashes") not in (None, "[] 0") for drawing in drawings)
        assert any(
            isinstance(opacity := drawing.get("fill_opacity"), int | float) and opacity < 1.0
            for drawing in drawings
        )
        text = page.get_text()
        assert "Panel B: dashed cubic Bezier curve" in text
        assert "Panel C: closed polygon with translucent fill" in text
        assert "The fixture uses no raster image or external asset." in text


def test_main_writes_machine_readable_evidence(tmp_path: Path, capsys: object) -> None:
    output = tmp_path / "corpus"
    evidence = tmp_path / "evidence" / "generated.json"

    exit_code = _MODULE.main([str(output), "--evidence", str(evidence)])

    assert exit_code == 0
    persisted = json.loads(evidence.read_text(encoding="utf-8"))
    assert persisted["case_count"] == 7
    assert persisted["cases"][0]["case_id"] == "annotated_form"
    assert persisted["cases"][0]["pages"][0]["annotation_count"] == 1
    assert persisted["cases"][0]["pages"][0]["widget_count"] == 1
    assert persisted["cases"][1]["case_id"] == "image_heavy"
    assert persisted["cases"][1]["pages"][0]["image_occurrence_count"] == 3
    assert persisted["cases"][1]["pages"][0]["embedded_image_count"] == 2
    assert persisted["cases"][3]["case_id"] == "rotated_cropped"
    assert persisted["cases"][3]["pages"][0]["rotation"] == 90
    assert persisted["cases"][5]["case_id"] == "table_heavy"
    assert persisted["cases"][5]["pages"][0]["table_count"] >= 1
    assert persisted["cases"][6]["case_id"] == "vector_heavy"
    assert persisted["cases"][6]["pages"][0]["drawing_count"] == 4
    assert persisted["cases"][6]["pages"][0]["drawing_item_count"] >= 8
    captured = capsys.readouterr()
    printed = json.loads(captured.out)
    assert printed["evidence"] == str(evidence.resolve())
