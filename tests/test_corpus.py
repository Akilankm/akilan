from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

import fitz
import pytest

from akilan.corpus import CorpusSourceError, load_corpus_sources, sync_corpus


def _pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "AKILAN corpus fixture")
    payload = document.tobytes()
    document.close()
    return payload


def _write_manifest(path: Path, *, sha256: str | None = None, filename: str = "fixture.pdf") -> None:
    source: dict[str, Any] = {
        "id": "fixture",
        "url": "https://example.test/fixture.pdf",
        "filename": filename,
        "source_page": "https://example.test/source",
        "purpose": "Generated test fixture",
    }
    if sha256 is not None:
        source["sha256"] = sha256
    path.write_text(json.dumps({"version": 1, "sources": [source]}), encoding="utf-8")


class _Response(io.BytesIO):
    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def test_sync_corpus_downloads_valid_pdf_atomically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _pdf_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    manifest = tmp_path / "sources.json"
    _write_manifest(manifest, sha256=digest, filename="public/fixture.pdf")
    monkeypatch.setattr("akilan.corpus.urlopen", lambda *_args, **_kwargs: _Response(payload))

    result = sync_corpus(manifest, tmp_path / "data")

    assert len(result) == 1
    assert result[0].status == "downloaded"
    assert result[0].sha256 == digest
    assert result[0].page_count == 1
    assert result[0].path.read_bytes() == payload
    assert not list(result[0].path.parent.glob(".fixture.pdf.*"))


def test_sync_corpus_reuses_existing_valid_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _pdf_bytes()
    manifest = tmp_path / "sources.json"
    _write_manifest(manifest, sha256=hashlib.sha256(payload).hexdigest())
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "fixture.pdf").write_bytes(payload)

    def fail_urlopen(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network must not be used for an existing valid file")

    monkeypatch.setattr("akilan.corpus.urlopen", fail_urlopen)
    result = sync_corpus(manifest, data_dir)

    assert result[0].status == "existing"
    assert result[0].page_count == 1


def test_sync_corpus_rejects_invalid_pdf_and_cleans_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "sources.json"
    _write_manifest(manifest)
    monkeypatch.setattr("akilan.corpus.urlopen", lambda *_args, **_kwargs: _Response(b"not a pdf"))

    with pytest.raises(CorpusSourceError, match="invalid PDF"):
        sync_corpus(manifest, tmp_path / "data")

    assert not (tmp_path / "data" / "fixture.pdf").exists()
    assert not list((tmp_path / "data").glob(".fixture.pdf.*"))


def test_sync_corpus_enforces_streaming_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "sources.json"
    _write_manifest(manifest)
    monkeypatch.setattr("akilan.corpus.urlopen", lambda *_args, **_kwargs: _Response(_pdf_bytes()))

    with pytest.raises(CorpusSourceError, match="exceeds"):
        sync_corpus(manifest, tmp_path / "data", max_bytes=10)


def test_load_corpus_sources_rejects_unsafe_filename(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.json"
    _write_manifest(manifest, filename="../escape.pdf")

    with pytest.raises(CorpusSourceError, match="safe relative"):
        load_corpus_sources(manifest)
