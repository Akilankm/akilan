from __future__ import annotations

import json
import re
from pathlib import Path


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def test_public_corpus_sources_are_checksum_pinned() -> None:
    manifest_path = Path(__file__).parents[1] / "data" / "sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    sources = manifest["sources"]
    assert sources, "the public benchmark corpus must declare at least one source"

    identifiers: set[str] = set()
    filenames: set[str] = set()
    for source in sources:
        identifier = source["id"]
        filename = source["filename"]
        digest = source.get("sha256", "")

        assert identifier not in identifiers, f"duplicate corpus source id: {identifier}"
        assert filename not in filenames, f"duplicate corpus destination: {filename}"
        assert _SHA256.fullmatch(digest), f"source {identifier} is not pinned by a lowercase SHA-256 digest"

        identifiers.add(identifier)
        filenames.add(filename)
