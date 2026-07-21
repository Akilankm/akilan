"""Read-only PDF source preflight diagnostics.

The preflight boundary classifies source failures before artifact construction while
preserving PyMuPDF as the only runtime dependency. It never repairs, rewrites, or
publishes an artifact.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import pymupdf

PDFPreflightStatus = Literal[
    "ready",
    "missing",
    "not_a_file",
    "empty_file",
    "unreadable_pdf",
    "not_pdf",
    "password_required",
    "invalid_password",
    "zero_pages",
]


@dataclass(frozen=True, slots=True)
class PDFPreflightReport:
    """Deterministic evidence describing whether a PDF can enter extraction."""

    status: PDFPreflightStatus
    source_path: str
    size_bytes: int | None
    page_count: int | None = None
    is_pdf: bool | None = None
    is_encrypted: bool | None = None
    needs_password: bool | None = None
    is_repaired: bool | None = None
    error_type: str | None = None
    message: str | None = None

    @property
    def accepted(self) -> bool:
        """Return whether the source is ready for artifact construction."""

        return self.status == "ready"

    def to_dict(self) -> dict[str, Any]:
        """Return stable machine-readable evidence."""

        return asdict(self)


def _report(
    status: PDFPreflightStatus,
    source: Path,
    *,
    size_bytes: int | None,
    **evidence: Any,
) -> PDFPreflightReport:
    return PDFPreflightReport(
        status=status,
        source_path=str(source),
        size_bytes=size_bytes,
        **evidence,
    )


def preflight_pdf(
    pdf_path: str | Path,
    *,
    password: str | None = None,
) -> PDFPreflightReport:
    """Inspect a PDF source without producing or modifying an artifact.

    Repaired PDFs are reported through ``is_repaired`` but are not rejected solely
    for being repaired. This keeps the boundary evidence-first: callers may impose
    a stricter policy without losing PyMuPDF's observable recovery information.
    """

    source = Path(pdf_path).expanduser().resolve()
    if not source.exists():
        return _report("missing", source, size_bytes=None, message="Source path does not exist")
    if not source.is_file():
        return _report("not_a_file", source, size_bytes=None, message="Source path is not a file")

    try:
        size_bytes = source.stat().st_size
    except OSError as exc:
        return _report(
            "unreadable_pdf",
            source,
            size_bytes=None,
            error_type=type(exc).__name__,
            message=str(exc),
        )
    if size_bytes == 0:
        return _report("empty_file", source, size_bytes=0, message="Source file is empty")

    try:
        document = pymupdf.open(source)
    except (pymupdf.EmptyFileError, pymupdf.FileDataError) as exc:
        return _report(
            "unreadable_pdf",
            source,
            size_bytes=size_bytes,
            error_type=type(exc).__name__,
            message=str(exc),
        )
    except OSError as exc:
        return _report(
            "unreadable_pdf",
            source,
            size_bytes=size_bytes,
            error_type=type(exc).__name__,
            message=str(exc),
        )

    try:
        needs_password = bool(document.needs_pass)
        is_encrypted = bool(document.is_encrypted)
        is_repaired = bool(document.is_repaired)
        if needs_password:
            if password is None:
                return _report(
                    "password_required",
                    source,
                    size_bytes=size_bytes,
                    is_pdf=bool(document.is_pdf),
                    is_encrypted=is_encrypted,
                    needs_password=True,
                    is_repaired=is_repaired,
                    message="The PDF requires a password",
                )
            if not document.authenticate(password):
                return _report(
                    "invalid_password",
                    source,
                    size_bytes=size_bytes,
                    is_pdf=bool(document.is_pdf),
                    is_encrypted=is_encrypted,
                    needs_password=True,
                    is_repaired=is_repaired,
                    message="The supplied password is invalid",
                )

        is_pdf = bool(document.is_pdf)
        if not is_pdf:
            return _report(
                "not_pdf",
                source,
                size_bytes=size_bytes,
                is_pdf=False,
                is_encrypted=is_encrypted,
                needs_password=needs_password,
                is_repaired=is_repaired,
                message="The opened document is not a PDF",
            )

        page_count = int(document.page_count)
        if page_count == 0:
            return _report(
                "zero_pages",
                source,
                size_bytes=size_bytes,
                page_count=0,
                is_pdf=True,
                is_encrypted=is_encrypted,
                needs_password=needs_password,
                is_repaired=is_repaired,
                message="The PDF contains no pages",
            )

        return _report(
            "ready",
            source,
            size_bytes=size_bytes,
            page_count=page_count,
            is_pdf=True,
            is_encrypted=is_encrypted,
            needs_password=needs_password,
            is_repaired=is_repaired,
        )
    finally:
        document.close()


__all__ = ["PDFPreflightReport", "PDFPreflightStatus", "preflight_pdf"]
