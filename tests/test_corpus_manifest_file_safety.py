from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from akilan.corpus import CorpusSourceError, load_corpus_sources


def _manifest_payload() -> str:
    return json.dumps(
        {
            "version": 1,
            "sources": [
                {
                    "id": "fixture",
                    "url": "https://example.test/fixture.pdf",
                    "filename": "fixture.pdf",
                    "source_page": "https://example.test/source",
                    "purpose": "Generated test fixture",
                }
            ],
        }
    )


def test_load_corpus_sources_reads_regular_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.json"
    manifest.write_text(_manifest_payload(), encoding="utf-8")

    sources = load_corpus_sources(manifest)

    assert [source.source_id for source in sources] == ["fixture"]


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="platform lacks O_NOFOLLOW")
def test_load_corpus_sources_rejects_symbolic_link_without_mutating_target(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text(_manifest_payload(), encoding="utf-8")
    manifest = tmp_path / "sources.json"
    manifest.symlink_to(target)
    original = target.read_bytes()

    with pytest.raises(CorpusSourceError, match="Unable to read corpus manifest"):
        load_corpus_sources(manifest)

    assert target.read_bytes() == original
    assert manifest.is_symlink()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="platform lacks FIFO support")
def test_load_corpus_sources_rejects_fifo_without_blocking(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.json"
    os.mkfifo(manifest)

    with pytest.raises(CorpusSourceError, match="must be a regular file"):
        load_corpus_sources(manifest)

    assert manifest.exists()
