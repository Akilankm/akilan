from __future__ import annotations

import hashlib
import json
from email.message import Message
from pathlib import Path

import pytest

from akilan.public_corpus import PublicCorpusError, download_public_corpus, load_public_corpus_manifest


class _Response:
    def __init__(self, payload: bytes, content_type: str = "application/pdf") -> None:
        self._payload = payload
        self._offset = 0
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def _manifest(path: Path, *, sha256: str | None = None, url: str = "https://example.test/doc.pdf") -> Path:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "entries": [
                    {
                        "name": "fixture",
                        "url": url,
                        "filename": "fixture.pdf",
                        "sha256": sha256,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_load_manifest_rejects_insecure_url(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path / "manifest.json", url="http://example.test/doc.pdf")

    with pytest.raises(PublicCorpusError, match="must use https"):
        load_public_corpus_manifest(manifest)


def test_download_validates_and_reuses_pinned_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"%PDF-1.7\nfixture\n%%EOF\n"
    digest = hashlib.sha256(payload).hexdigest()
    manifest = _manifest(tmp_path / "manifest.json", sha256=digest)
    destination = tmp_path / "data"
    calls = 0

    def fake_urlopen(*_args: object, **_kwargs: object) -> _Response:
        nonlocal calls
        calls += 1
        return _Response(payload)

    monkeypatch.setattr("akilan.public_corpus.urlopen", fake_urlopen)

    first = download_public_corpus(manifest, destination)
    second = download_public_corpus(manifest, destination)

    assert first[0].reused is False
    assert second[0].reused is True
    assert first[0].sha256 == digest
    assert first[0].path.read_bytes() == payload
    assert calls == 1
    assert not list(destination.glob("*.tmp"))


def test_download_rejects_non_pdf_without_publishing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(tmp_path / "manifest.json")
    destination = tmp_path / "data"
    monkeypatch.setattr(
        "akilan.public_corpus.urlopen",
        lambda *_args, **_kwargs: _Response(b"not a pdf"),
    )

    with pytest.raises(PublicCorpusError, match="not a PDF"):
        download_public_corpus(manifest, destination)

    assert not (destination / "fixture.pdf").exists()
    assert not list(destination.glob("*.tmp"))


def test_download_rejects_digest_mismatch_without_overwriting_existing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path / "manifest.json", sha256="0" * 64)
    destination = tmp_path / "data"
    destination.mkdir()
    target = destination / "fixture.pdf"
    original = b"%PDF-1.4\noriginal\n%%EOF\n"
    target.write_bytes(original)
    monkeypatch.setattr(
        "akilan.public_corpus.urlopen",
        lambda *_args, **_kwargs: _Response(b"%PDF-1.7\nreplacement\n%%EOF\n"),
    )

    with pytest.raises(PublicCorpusError, match="SHA-256 mismatch"):
        download_public_corpus(manifest, destination, overwrite=True)

    assert target.read_bytes() == original
