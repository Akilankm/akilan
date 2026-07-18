from __future__ import annotations

import json
from pathlib import Path


def test_public_corpus_sources_are_checksum_pinned() -> None:
    manifest_path = Path(__file__).parents[1] / "data" / "sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = manifest["sources"]

    assert sources
    assert len({source["id"] for source in sources}) == len(sources)
    assert len({source["filename"] for source in sources}) == len(sources)

    for source in sources:
        digest = source.get("sha256", "")
        assert len(digest) == 64
        assert digest == digest.lower()
        assert all(character in "0123456789abcdef" for character in digest)
