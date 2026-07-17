"""Command-line interface for AKILAN."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import ExtractionConfig
from .extraction import PDFArtifactBuilder
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="akilan",
        description="Build a deterministic geometry-aware AI artifact from a PDF using PyMuPDF.",
    )
    parser.add_argument("--version", action="version", version=f"akilan {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract = subparsers.add_parser("extract", help="Extract a PDF into an artifact directory")
    extract.add_argument("pdf", type=Path)
    extract.add_argument("--output", "-o", type=Path, required=True)
    extract.add_argument("--password")
    extract.add_argument("--overwrite", action="store_true")
    extract.add_argument("--include-characters", action="store_true")
    extract.add_argument("--render-pages", action="store_true")
    extract.add_argument("--render-dpi", type=int, default=144)
    extract.add_argument("--no-tables", action="store_true")
    extract.add_argument("--no-images", action="store_true")
    extract.add_argument("--no-drawings", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "extract":
        return 2
    config = ExtractionConfig(
        include_characters=args.include_characters,
        render_pages=args.render_pages,
        render_dpi=args.render_dpi,
        extract_tables=not args.no_tables,
        extract_images=not args.no_images,
        extract_drawings=not args.no_drawings,
        overwrite=args.overwrite,
    )
    artifact = PDFArtifactBuilder(config).build(args.pdf, args.output, password=args.password)
    print(
        json.dumps(
            {
                "artifact": str(args.output.resolve()),
                "pages": artifact.statistics["page_count"],
                "text_blocks": artifact.statistics["text_block_count"],
                "tables": artifact.statistics["table_count"],
                "images": artifact.statistics["image_count"],
            },
            indent=2,
        )
    )
    return 0
