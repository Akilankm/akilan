"""Public convenience API."""

from __future__ import annotations

from pathlib import Path

from .config import ExtractionConfig
from .extraction import PDFArtifactBuilder
from .models import DocumentArtifact


def build_artifact(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    config: ExtractionConfig | None = None,
    password: str | None = None,
) -> DocumentArtifact:
    """Build an AI-friendly PDF artifact using only PyMuPDF at runtime."""

    return PDFArtifactBuilder(config=config).build(pdf_path, output_dir, password=password)
