"""Reproducible acquisition of public PDF benchmark sources."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

import fitz


class CorpusSourceError(RuntimeError):
    """Raised when a corpus source cannot be acquired safely."""


@dataclass(frozen=True, slots=True)
class CorpusSource:
    """One public PDF source declared in a corpus manifest."""

    source_id: str
    url: str
    filename: str
    source_page: str
    purpose: str
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class CorpusDownload:
    """Result of synchronizing one corpus source."""

    source_id: str
    path: Path
    status: str
    sha256: str
    size_bytes: int
    page_count: int


def load_corpus_sources(path: str | Path) -> tuple[CorpusSource, ...]:
    """Load and strictly validate a JSON corpus-source manifest."""
    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusSourceError(f"Unable to read corpus manifest {manifest_path}: {exc}") from exc

    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise CorpusSourceError("Corpus manifest must be an object with version 1")
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise CorpusSourceError("Corpus manifest must contain a non-empty sources list")

    sources: list[CorpusSource] = []
    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    for index, raw in enumerate(raw_sources):
        if not isinstance(raw, dict):
            raise CorpusSourceError(f"sources[{index}] must be an object")
        required = ("id", "url", "filename", "source_page", "purpose")
        missing = [key for key in required if not isinstance(raw.get(key), str) or not raw[key].strip()]
        if missing:
            raise CorpusSourceError(f"sources[{index}] has missing or empty fields: {', '.join(missing)}")

        source_id = raw["id"].strip()
        url = raw["url"].strip()
        filename = raw["filename"].strip()
        source_page = raw["source_page"].strip()
        purpose = raw["purpose"].strip()
        sha256 = raw.get("sha256")

        if not url.startswith("https://") or not source_page.startswith("https://"):
            raise CorpusSourceError(f"{source_id}: url and source_page must use HTTPS")
        safe_path = PurePosixPath(filename)
        if safe_path.is_absolute() or ".." in safe_path.parts or safe_path.suffix.lower() != ".pdf":
            raise CorpusSourceError(f"{source_id}: filename must be a safe relative .pdf path")
        if source_id in seen_ids or filename.casefold() in seen_files:
            raise CorpusSourceError(f"{source_id}: duplicate source id or filename")
        if sha256 is not None:
            if not isinstance(sha256, str) or len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
                raise CorpusSourceError(f"{source_id}: sha256 must be 64 lowercase hexadecimal characters")

        seen_ids.add(source_id)
        seen_files.add(filename.casefold())
        sources.append(CorpusSource(source_id, url, filename, source_page, purpose, sha256))

    return tuple(sources)


def sync_corpus(
    manifest_path: str | Path,
    data_dir: str | Path,
    *,
    overwrite: bool = False,
    timeout_seconds: float = 30.0,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[CorpusDownload, ...]:
    """Download, verify, validate, and atomically publish all declared PDFs."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    destination_root = Path(data_dir)
    destination_root.mkdir(parents=True, exist_ok=True)
    results: list[CorpusDownload] = []
    for source in load_corpus_sources(manifest_path):
        destination = destination_root / Path(source.filename)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not overwrite:
            digest, size_bytes, page_count = _inspect_pdf(destination)
            if source.sha256 is not None and digest != source.sha256:
                raise CorpusSourceError(f"{source.source_id}: existing file checksum does not match manifest")
            results.append(CorpusDownload(source.source_id, destination, "existing", digest, size_bytes, page_count))
            continue

        results.append(_download_source(source, destination, timeout_seconds, max_bytes))
    return tuple(results)


def _download_source(source: CorpusSource, destination: Path, timeout_seconds: float, max_bytes: int) -> CorpusDownload:
    request = Request(source.url, headers={"User-Agent": "AKILAN-corpus/0.1"})
    temp_path: Path | None = None
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            if not final_url.startswith("https://"):
                raise CorpusSourceError(f"{source.source_id}: download redirected to a non-HTTPS URL")
            declared_length = response.headers.get("Content-Length")
            if declared_length is not None and int(declared_length) > max_bytes:
                raise CorpusSourceError(f"{source.source_id}: declared file size exceeds {max_bytes} bytes")

            with tempfile.NamedTemporaryFile("wb", delete=False, dir=destination.parent, prefix=f".{destination.name}.") as handle:
                temp_path = Path(handle.name)
                digest = hashlib.sha256()
                size_bytes = 0
                while chunk := response.read(1024 * 1024):
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        raise CorpusSourceError(f"{source.source_id}: download exceeds {max_bytes} bytes")
                    digest.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())

        actual_sha256 = digest.hexdigest()
        if source.sha256 is not None and actual_sha256 != source.sha256:
            raise CorpusSourceError(f"{source.source_id}: downloaded checksum does not match manifest")
        inspected_sha256, inspected_size, page_count = _inspect_pdf(temp_path)
        if inspected_sha256 != actual_sha256 or inspected_size != size_bytes:
            raise CorpusSourceError(f"{source.source_id}: downloaded file changed before validation")
        os.replace(temp_path, destination)
        temp_path = None
        return CorpusDownload(source.source_id, destination, "downloaded", actual_sha256, size_bytes, page_count)
    except CorpusSourceError:
        raise
    except Exception as exc:
        raise CorpusSourceError(f"{source.source_id}: failed to download or validate PDF: {exc}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _inspect_pdf(path: Path) -> tuple[str, int, int]:
    digest = hashlib.sha256()
    size_bytes = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size_bytes += len(chunk)
        with fitz.open(path) as document:
            if not document.is_pdf or document.page_count < 1:
                raise CorpusSourceError(f"{path}: file is not a non-empty PDF")
            page_count = document.page_count
    except CorpusSourceError:
        raise
    except Exception as exc:
        raise CorpusSourceError(f"{path}: invalid PDF: {exc}") from exc
    return digest.hexdigest(), size_bytes, page_count
