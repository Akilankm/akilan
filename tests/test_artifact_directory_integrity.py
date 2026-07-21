from __future__ import annotations

import hashlib

import akilan.artifact_directory_integrity as integrity_module
from akilan.artifact_directory_integrity import assess_artifact_directory_integrity


def test_complete_directory_integrity_is_deterministic(tmp_path) -> None:
    root = tmp_path / "artifact"
    assets = root / "assets"
    assets.mkdir(parents=True)
    document = root / "document.json"
    image = assets / "image.bin"
    document.write_bytes(b'{"schema_version":"1.0.0"}')
    image.write_bytes(b"image-evidence")

    first = assess_artifact_directory_integrity(root)
    second = assess_artifact_directory_integrity(root)

    assert first.accepted is True
    assert first.status == "accepted"
    assert first.file_count == 2
    assert first.total_size_bytes == document.stat().st_size + image.stat().st_size
    assert [entry.relative_path for entry in first.files] == [
        "assets/image.bin",
        "document.json",
    ]
    assert first.files[0].sha256 == hashlib.sha256(image.read_bytes()).hexdigest()
    assert first.fingerprint == second.fingerprint
    assert first.to_dict() == second.to_dict()


def test_fingerprint_changes_when_any_artifact_file_changes(tmp_path) -> None:
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "document.json").write_text("{}", encoding="utf-8")
    projection = root / "document.md"
    projection.write_text("first", encoding="utf-8")

    first = assess_artifact_directory_integrity(root)
    projection.write_text("second", encoding="utf-8")
    second = assess_artifact_directory_integrity(root)

    assert first.accepted is True
    assert second.accepted is True
    assert first.fingerprint != second.fingerprint


def test_concurrent_mutation_rejects_complete_directory_without_partial_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "document.json").write_text("{}", encoding="utf-8")
    (root / "projection.md").write_text("content", encoding="utf-8")
    original_read = integrity_module._read_stable_regular_file

    def changing_read(path):
        if path.name == "projection.md":
            raise RuntimeError("changed_during_read")
        return original_read(path)

    monkeypatch.setattr(integrity_module, "_read_stable_regular_file", changing_read)

    report = assess_artifact_directory_integrity(root)

    assert report.accepted is False
    assert report.status == "changed_during_read"
    assert report.files == ()
    assert report.file_count == 0
    assert report.total_size_bytes == 0


def test_missing_document_rejects_directory_without_partial_evidence(tmp_path) -> None:
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "projection.md").write_text("content", encoding="utf-8")

    report = assess_artifact_directory_integrity(root)

    assert report.accepted is False
    assert report.status == "missing_document"
    assert report.files == ()
    assert report.file_count == 0


def test_missing_and_non_directory_sources_fail_closed(tmp_path) -> None:
    missing = assess_artifact_directory_integrity(tmp_path / "missing")
    source_file = tmp_path / "artifact.json"
    source_file.write_text("{}", encoding="utf-8")
    not_directory = assess_artifact_directory_integrity(source_file)

    assert missing.status == "missing"
    assert not_directory.status == "not_a_directory"
    assert missing.accepted is False
    assert not_directory.accepted is False


def test_symlink_is_rejected_without_following_target(tmp_path) -> None:
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "document.json").write_text("{}", encoding="utf-8")
    external = tmp_path / "external.bin"
    external.write_bytes(b"external")
    link = root / "external-link.bin"
    try:
        link.symlink_to(external)
    except OSError:
        return

    report = assess_artifact_directory_integrity(root)

    assert report.accepted is False
    assert report.status == "symlink_rejected"
    assert report.files == ()
