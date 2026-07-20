from __future__ import annotations

import json
from pathlib import Path

from akilan.corpus import CorpusDownload, CorpusVerification
from akilan.corpus_cli import main


def test_sync_cli_emits_machine_readable_evidence(monkeypatch, tmp_path: Path, capsys) -> None:
    result = CorpusDownload("sample", tmp_path / "sample.pdf", "downloaded", "a" * 64, 123, 2)
    monkeypatch.setattr("akilan.corpus_cli.sync_corpus", lambda *_args, **_kwargs: (result,))

    exit_code = main(["sync", "data/sources.json", "--data-dir", str(tmp_path)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["sources"][0]["status"] == "downloaded"
    assert payload["sources"][0]["page_count"] == 2


def test_verify_cli_fails_closed_for_missing_source(monkeypatch, tmp_path: Path, capsys) -> None:
    result = CorpusVerification(
        "sample",
        tmp_path / "sample.pdf",
        "missing",
        None,
        None,
        None,
        None,
        "file is missing",
    )
    monkeypatch.setattr("akilan.corpus_cli.verify_corpus", lambda *_args, **_kwargs: (result,))

    exit_code = main(["verify", "data/sources.json", "--data-dir", str(tmp_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.err)

    assert exit_code == 1
    assert captured.out == ""
    assert payload["ok"] is False
    assert payload["sources"][0]["status"] == "missing"


def test_verify_cli_succeeds_only_when_all_sources_are_valid(monkeypatch, tmp_path: Path, capsys) -> None:
    result = CorpusVerification(
        "sample",
        tmp_path / "sample.pdf",
        "valid",
        "b" * 64,
        "b" * 64,
        456,
        3,
    )
    monkeypatch.setattr("akilan.corpus_cli.verify_corpus", lambda *_args, **_kwargs: (result,))

    exit_code = main(["verify", "data/sources.json", "--data-dir", str(tmp_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert payload["ok"] is True
    assert payload["sources"][0]["actual_sha256"] == "b" * 64
