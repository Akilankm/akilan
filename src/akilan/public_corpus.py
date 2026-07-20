"""Reproducible, fail-closed download support for public PDF test corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_PDF_MAGIC = b"%PDF-"
_USER_AGENT = "akilan-public-corpus/0.1"


class PublicCorpusError(RuntimeError):
    """Raised when a public corpus manifest or download is unsafe or invalid."""


@dataclass(frozen=True)
class PublicPDFEntry:
    """One immutable public PDF corpus entry."""

    name: str
    url: str
    filename: str
    sha256: str | None = None


@dataclass(frozen=True)
class PublicCorpusDownload:
    """Evidence returned after one corpus file is validated and published."""

    name: str
    path: Path
    sha256: str
    size_bytes: int
    reused: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "reused": self.reused,
        }


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicCorpusError(f"{field} must be a non-empty string")
    return value.strip()


def _parse_entry(raw: object, index: int) -> PublicPDFEntry:
    if not isinstance(raw, dict):
        raise PublicCorpusError(f"entries[{index}] must be an object")
    name = _require_text(raw.get("name"), f"entries[{index}].name")
    url = _require_text(raw.get("url"), f"entries[{index}].url")
    filename = _require_text(raw.get("filename"), f"entries[{index}].filename")
    if not url.startswith("https://"):
        raise PublicCorpusError(f"entries[{index}].url must use https")
    candidate = Path(filename)
    if candidate.name != filename or candidate.suffix.lower() != ".pdf":
        raise PublicCorpusError(f"entries[{index}].filename must be a plain .pdf filename")
    sha256 = raw.get("sha256")
    if sha256 is not None:
        sha256 = _require_text(sha256, f"entries[{index}].sha256").lower()
        if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
            raise PublicCorpusError(f"entries[{index}].sha256 must be a lowercase SHA-256 digest")
    return PublicPDFEntry(name=name, url=url, filename=filename, sha256=sha256)


def load_public_corpus_manifest(path: str | Path) -> tuple[PublicPDFEntry, ...]:
    """Load and validate a deterministic public corpus manifest."""

    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicCorpusError(f"cannot read corpus manifest {manifest_path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise PublicCorpusError("corpus manifest version must be integer 1")
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise PublicCorpusError("corpus manifest entries must be a non-empty array")
    entries = tuple(_parse_entry(raw, index) for index, raw in enumerate(raw_entries))
    filenames = [entry.filename for entry in entries]
    if len(filenames) != len(set(filenames)):
        raise PublicCorpusError("corpus manifest contains duplicate filenames")
    return entries


def _inspect_pdf(path: Path, expected_sha256: str | None) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            prefix = stream.read(len(_PDF_MAGIC))
            if prefix != _PDF_MAGIC:
                raise PublicCorpusError(f"downloaded content is not a PDF: {path}")
            digest.update(prefix)
            size += len(prefix)
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise PublicCorpusError(f"cannot inspect downloaded file {path}: {exc}") from exc
    actual = digest.hexdigest()
    if expected_sha256 is not None and actual != expected_sha256:
        raise PublicCorpusError(
            f"SHA-256 mismatch for {path.name}: expected {expected_sha256}, received {actual}"
        )
    return actual, size


def download_public_corpus(
    manifest: str | Path,
    destination: str | Path,
    *,
    overwrite: bool = False,
    timeout_seconds: float = 60.0,
) -> tuple[PublicCorpusDownload, ...]:
    """Download, validate, and atomically publish every manifest PDF."""

    if timeout_seconds <= 0:
        raise PublicCorpusError("timeout_seconds must be greater than zero")
    entries = load_public_corpus_manifest(manifest)
    destination_path = Path(destination)
    destination_path.mkdir(parents=True, exist_ok=True)
    results: list[PublicCorpusDownload] = []
    for entry in entries:
        target = destination_path / entry.filename
        if target.exists() and not overwrite:
            digest, size = _inspect_pdf(target, entry.sha256)
            results.append(PublicCorpusDownload(entry.name, target, digest, size, True))
            continue
        request = Request(entry.url, headers={"User-Agent": _USER_AGENT})
        temporary_path: Path | None = None
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                content_type = response.headers.get_content_type()
                if content_type not in {"application/pdf", "application/octet-stream"}:
                    raise PublicCorpusError(
                        f"unexpected content type for {entry.name}: {content_type}"
                    )
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{entry.filename}.",
                    suffix=".tmp",
                    dir=destination_path,
                    delete=False,
                ) as temporary:
                    temporary_path = Path(temporary.name)
                    while chunk := response.read(1024 * 1024):
                        temporary.write(chunk)
                    temporary.flush()
                    os.fsync(temporary.fileno())
            digest, size = _inspect_pdf(temporary_path, entry.sha256)
            temporary_path.replace(target)
            results.append(PublicCorpusDownload(entry.name, target, digest, size, False))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise PublicCorpusError(f"failed to download {entry.name} from {entry.url}: {exc}") from exc
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
    return tuple(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download AKILAN's reproducible public PDF corpus")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--destination", type=Path, default=Path("data/public"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)
    try:
        results = download_public_corpus(
            args.manifest,
            args.destination,
            overwrite=args.overwrite,
            timeout_seconds=args.timeout,
        )
    except PublicCorpusError as exc:
        parser.error(str(exc))
    print(json.dumps({"downloads": [result.to_dict() for result in results]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
