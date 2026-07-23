from __future__ import annotations

import json

from akilan.builder import _write_pages
from akilan.geometry import BBox
from akilan.models import PageArtifact


def _page_with_relationship_evidence() -> PageArtifact:
    return PageArtifact(
        page_index=0,
        page_number=1,
        label="1",
        width=595.0,
        height=842.0,
        rotation=0,
        mediabox=BBox(0.0, 0.0, 595.0, 842.0),
        cropbox=BBox(0.0, 0.0, 595.0, 842.0),
        json_path="pages/page_0001.json",
        metrics={
            "relationship_evidence": [
                {
                    "source_id": "heading-1",
                    "target_id": "body-1",
                    "relationship": "contains",
                    "rule_id": "direct-section-containment-v1",
                    "confidence": 0.9,
                }
            ],
            "relationship_ambiguities": [
                {
                    "source_id": "caption-1",
                    "relationship": "describes",
                    "rule_id": "caption-candidate-margin-v1",
                    "candidate_ids": ["table-1", "table-2"],
                }
            ],
        },
    )


def test_write_pages_preserves_relationship_metrics(tmp_path) -> None:
    page = _page_with_relationship_evidence()
    (tmp_path / "pages").mkdir()

    _write_pages(tmp_path, [page])

    persisted = json.loads((tmp_path / "pages" / "page_0001.json").read_text(encoding="utf-8"))
    assert persisted["metrics"]["relationship_evidence"] == page.metrics["relationship_evidence"]
    assert persisted["metrics"]["relationship_ambiguities"] == page.metrics["relationship_ambiguities"]
    assert "text_block_count" in persisted["metrics"]


def test_write_pages_is_idempotent_for_owned_relationship_metrics(tmp_path) -> None:
    page = _page_with_relationship_evidence()
    expected = json.loads(json.dumps(page.metrics))
    (tmp_path / "pages").mkdir()

    _write_pages(tmp_path, [page])
    _write_pages(tmp_path, [page])

    assert page.metrics["relationship_evidence"] == expected["relationship_evidence"]
    assert page.metrics["relationship_ambiguities"] == expected["relationship_ambiguities"]
