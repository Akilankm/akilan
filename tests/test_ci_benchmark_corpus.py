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

    assert payload["case_count"] == 3
    assert [case["case_id"] for case in payload["cases"]] == [
        "mixed_layout",
        "rotated_cropped",
        "single_column",
    ]
    assert sorted(path.name for path in output.glob("*.pdf")) == [
        "mixed_layout.pdf",
        "rotated_cropped.pdf",
        "single_column.pdf",
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


def test_main_writes_machine_readable_evidence(tmp_path: Path, capsys: object) -> None:
    output = tmp_path / "corpus"
    evidence = tmp_path / "evidence" / "generated.json"

    exit_code = _MODULE.main([str(output), "--evidence", str(evidence)])

    assert exit_code == 0
    persisted = json.loads(evidence.read_text(encoding="utf-8"))
    assert persisted["case_count"] == 3
    assert persisted["cases"][1]["case_id"] == "rotated_cropped"
    assert persisted["cases"][1]["pages"][0]["rotation"] == 90
    captured = capsys.readouterr()
    printed = json.loads(captured.out)
    assert printed["evidence"] == str(evidence.resolve())
