"""Command-line interface for AKILAN."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import run_corpus, write_corpus_report
from .config import ExtractionConfig
from .extraction import PDFArtifactBuilder
from .version import __version__


def _add_extraction_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--include-characters", action="store_true")
    parser.add_argument("--render-pages", action="store_true")
    parser.add_argument("--render-dpi", type=int, default=144)
    parser.add_argument("--no-tables", action="store_true")
    parser.add_argument("--no-images", action="store_true")
    parser.add_argument("--no-drawings", action="store_true")


def _config_from_args(args: argparse.Namespace, *, overwrite: bool) -> ExtractionConfig:
    return ExtractionConfig(
        include_characters=args.include_characters,
        render_pages=args.render_pages,
        render_dpi=args.render_dpi,
        extract_tables=not args.no_tables,
        extract_images=not args.no_images,
        extract_drawings=not args.no_drawings,
        overwrite=overwrite,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="akilan",
        description="Build deterministic geometry-aware PDF artifacts using PyMuPDF.",
    )
    parser.add_argument("--version", action="version", version=f"akilan {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="Extract a PDF into an artifact directory")
    extract.add_argument("pdf", type=Path)
    extract.add_argument("--output", "-o", type=Path, required=True)
    extract.add_argument("--password")
    extract.add_argument("--overwrite", action="store_true")
    _add_extraction_arguments(extract)

    benchmark = subparsers.add_parser(
        "benchmark",
        help="Extract every matching PDF in a corpus and write a machine-readable report",
    )
    benchmark.add_argument("corpus", type=Path, help="Directory containing benchmark PDFs")
    benchmark.add_argument("--output-root", type=Path, required=True)
    benchmark.add_argument("--report", type=Path, required=True)
    benchmark.add_argument("--pattern", default="*.pdf", help="Recursive glob pattern relative to the corpus directory")
    benchmark.add_argument("--no-cache", action="store_true", help="Force a cold benchmark run")
    _add_extraction_arguments(benchmark)
    return parser


def _run_extract(args: argparse.Namespace) -> int:
    config = _config_from_args(args, overwrite=args.overwrite)
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


def _run_benchmark(args: argparse.Namespace) -> int:
    corpus = args.corpus.expanduser().resolve()
    if not corpus.is_dir():
        raise SystemExit(f"benchmark corpus directory does not exist: {corpus}")

    pdf_paths = sorted(path for path in corpus.rglob(args.pattern) if path.is_file())
    if not pdf_paths:
        raise SystemExit(f"no benchmark PDFs matched {args.pattern!r} under {corpus}")

    report = run_corpus(
        pdf_paths,
        args.output_root,
        config=_config_from_args(args, overwrite=True),
        use_cache=not args.no_cache,
    )
    report_path = write_corpus_report(report, args.report)
    print(
        json.dumps(
            {
                "report": str(report_path),
                "total": len(report.cases),
                "succeeded": report.succeeded,
                "failed": report.failed,
            },
            indent=2,
        )
    )
    return 1 if report.failed else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "extract":
        return _run_extract(args)
    if args.command == "benchmark":
        return _run_benchmark(args)
    return 2
