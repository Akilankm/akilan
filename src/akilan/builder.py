"""Document-level PDF artifact orchestration."""

from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path
from typing import Any

import pymupdf

from .config import ExtractionConfig
from .extractors import (
    extract_annotations,
    extract_drawings,
    extract_images,
    extract_links,
    extract_tables,
    extract_text_blocks,
    extract_widgets,
)
from .geometry import BBox
from .layout import build_reading_order
from .models import DocumentArtifact, PageArtifact, TextBlock
from .native import sha256_file
from .projection import document_plain_text, document_statistics, page_markdown, page_metrics, render_page
from .semantics import assign_page_semantics, mark_repeated_headers_and_footers
from .serialization import dump_json, to_jsonable
from .version import __version__


class PDFExtractionError(RuntimeError):
    """Raised when a PDF cannot be converted into an artifact safely."""


def _embedded_files(doc: pymupdf.Document) -> list[dict[str, Any]]:
    try:
        names = doc.embfile_names()
    except Exception:
        return []
    result: list[dict[str, Any]] = []
    for name in names:
        try:
            info = doc.embfile_info(name)
        except Exception:
            info = {"name": name}
        result.append(to_jsonable(info))
    return result


def _prepare_output(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        if not overwrite:
            raise FileExistsError(f"Output directory is not empty: {output_dir}. Pass overwrite=True to replace it.")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def _extract_page(
    doc: pymupdf.Document,
    page_index: int,
    destination: Path,
    config: ExtractionConfig,
) -> PageArtifact:
    page = doc.load_page(page_index)
    page_rect = BBox.from_value(page.rect)
    text_blocks: list[TextBlock] = []
    image_blocks: list[dict[str, Any]] = []
    if config.extract_text or config.extract_images:
        text_blocks, image_blocks = extract_text_blocks(page, page_index, config.include_characters)
    tables = extract_tables(page, page_index) if config.extract_tables else []
    images = (
        extract_images(doc, page, page_index, image_blocks, destination / "assets" / "images", config)
        if config.extract_images
        else []
    )
    drawings = extract_drawings(page, page_index, config.min_drawing_area) if config.extract_drawings else []
    artifact = PageArtifact(
        page_index=page_index,
        page_number=page_index + 1,
        label=page.get_label() or str(page_index + 1),
        width=round(page_rect.width, 4),
        height=round(page_rect.height, 4),
        rotation=int(page.rotation),
        mediabox=BBox.from_value(page.mediabox),
        cropbox=BBox.from_value(page.cropbox),
        text_blocks=text_blocks if config.extract_text else [],
        tables=tables,
        images=images,
        drawings=drawings,
        links=extract_links(page, page_index) if config.extract_links else [],
        annotations=extract_annotations(page, page_index) if config.extract_annotations else [],
        widgets=extract_widgets(page, page_index) if config.extract_widgets else [],
    )
    assign_page_semantics(artifact, config.header_ratio, config.footer_ratio)
    artifact.reading_order = build_reading_order(
        page_width=artifact.width,
        text_blocks=artifact.text_blocks,
        tables=artifact.tables,
        images=artifact.images,
        drawings=artifact.drawings,
        suppress_table_text=config.suppress_table_text_in_reading_order,
    )
    if config.render_pages:
        render_path = destination / "assets" / "renders" / f"page_{page_index + 1:04d}.png"
        render_page(page, render_path, config.render_dpi)
        artifact.render_path = render_path.relative_to(destination).as_posix()
    artifact.json_path = f"pages/page_{page_index + 1:04d}.json"
    if config.include_page_markdown:
        artifact.markdown_path = f"pages/page_{page_index + 1:04d}.md"
    return artifact


def _document_metadata(doc: pymupdf.Document) -> dict[str, Any]:
    return {
        "page_count": doc.page_count,
        "metadata": to_jsonable(doc.metadata),
        "permissions": int(doc.permissions),
        "is_encrypted": bool(doc.is_encrypted),
        "needs_password": bool(doc.needs_pass),
        "is_repaired": bool(doc.is_repaired),
        "is_fast_webaccess": bool(doc.is_fast_webaccess),
        "page_layout": doc.pagelayout,
        "page_mode": doc.pagemode,
        "mark_info": to_jsonable(doc.markinfo),
    }


def _write_pages(destination: Path, pages: list[PageArtifact]) -> None:
    for page in pages:
        page.metrics = page_metrics(page)
        dump_json(destination / (page.json_path or ""), page)
        if page.markdown_path:
            (destination / page.markdown_path).write_text(page_markdown(page), encoding="utf-8")


class PDFArtifactBuilder:
    """Build a deterministic, geometry-aware, AI-friendly PDF artifact."""

    def __init__(self, config: ExtractionConfig | None = None):
        self.config = config or ExtractionConfig()
        self.config.validate()

    def build(
        self,
        pdf_path: str | Path,
        output_dir: str | Path,
        *,
        password: str | None = None,
    ) -> DocumentArtifact:
        source = Path(pdf_path).expanduser().resolve()
        destination = Path(output_dir).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        _prepare_output(destination, self.config.overwrite)
        (destination / "pages").mkdir(parents=True, exist_ok=True)
        (destination / "assets" / "images").mkdir(parents=True, exist_ok=True)

        doc = pymupdf.open(source)
        try:
            if doc.needs_pass and (not password or not doc.authenticate(password)):
                raise PDFExtractionError("The PDF is encrypted and the supplied password is missing or invalid")
            if not doc.is_pdf:
                raise PDFExtractionError(f"Input is not a PDF: {source}")

            pages = [_extract_page(doc, page_index, destination, self.config) for page_index in range(doc.page_count)]
            mark_repeated_headers_and_footers(
                pages,
                min_pages=self.config.repeated_margin_min_pages,
                min_fraction=self.config.repeated_margin_min_fraction,
            )
            _write_pages(destination, pages)
            mime_type, _ = mimetypes.guess_type(source.name)
            artifact = DocumentArtifact(
                schema_version="1.0.0",
                generator={"name": "akilan", "version": __version__, "engine": f"PyMuPDF {pymupdf.__version__}"},
                source={
                    "file_name": source.name,
                    "size_bytes": source.stat().st_size,
                    "mime_type": mime_type or "application/pdf",
                    "sha256": sha256_file(source),
                },
                document=_document_metadata(doc),
                table_of_contents=to_jsonable(doc.get_toc(simple=False)),
                embedded_files=_embedded_files(doc),
                pages=pages,
                statistics=document_statistics(pages),
            )
            renders_dir = destination / "assets" / "renders"
            artifact.artifact_files = {
                "manifest": "manifest.json",
                "document_json": "document.json",
                "document_markdown": "document.md" if self.config.include_document_markdown else None,
                "plain_text": "document.txt" if self.config.include_plain_text else None,
                "pages": [page.json_path for page in pages],
                "page_markdown": [page.markdown_path for page in pages if page.markdown_path],
                "images": sorted(path.relative_to(destination).as_posix() for path in (destination / "assets" / "images").glob("*")),
                "renders": sorted(path.relative_to(destination).as_posix() for path in renders_dir.glob("*")) if renders_dir.exists() else [],
            }
            dump_json(destination / "document.json", artifact)
            dump_json(
                destination / "manifest.json",
                {
                    "schema_version": artifact.schema_version,
                    "generator": artifact.generator,
                    "source": artifact.source,
                    "document": artifact.document,
                    "statistics": artifact.statistics,
                    "artifact_files": artifact.artifact_files,
                    "pages": [
                        {
                            "page_number": page.page_number,
                            "label": page.label,
                            "json_path": page.json_path,
                            "markdown_path": page.markdown_path,
                            "render_path": page.render_path,
                            "metrics": page.metrics,
                        }
                        for page in pages
                    ],
                },
            )
            if self.config.include_document_markdown:
                (destination / "document.md").write_text(
                    "\n\n".join(page_markdown(page).rstrip() for page in pages) + "\n",
                    encoding="utf-8",
                )
            if self.config.include_plain_text:
                (destination / "document.txt").write_text(document_plain_text(pages), encoding="utf-8")
            return artifact
        finally:
            doc.close()
