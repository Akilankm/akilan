"""Command-line interface for AKILAN."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .artifact_loader import load_artifact_directory
from .benchmark import run_corpus, write_corpus_report
from .config import ExtractionConfig
from .extraction import PDFArtifactBuilder
from .schema import ArtifactSchemaError
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


def _strip_terminal_newline(value: str) -> str:
    """Remove one terminal line ending while preserving intentional spaces."""

    if value.endswith("\r\n"):
        return value[:-2]
    if value.endswith(("\n", "\r")):
        return value[:-1]
    return value


def _password_from_args(args: argparse.Namespace) -> str | None:
    """Resolve an encrypted-PDF password from exactly one configured source."""

    if args.password is not None:
        return args.password
    if args.password_file is not None:
        try:
            value = args.password_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise SystemExit(f"cannot read password file {args.password_file}: {exc}") from exc
        password = _strip_terminal_newline(value)
        if not password:
            raise SystemExit(f"password file is empty: {args.password_file}")
        return password
    if args.password_stdin:
        password = _strip_terminal_newline(sys.stdin.readline())
        if not password:
            raise SystemExit("no password was received on standard input")
        return password
    return None


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
    password_group = extract.add_mutually_exclusive_group()
    password_group.add_argument(
        "--password",
        help="Encrypted-PDF password (visible to process listings and shell history)",
    )
    password_group.add_argument(
        "--password-file",
        type=Path,
        help="Read the encrypted-PDF password from a UTF-8 file",
    )
    password_group.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read one encrypted-PDF password line from standard input",
    )
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

    validate = subparsers.add_parser(
        "validate",
        help="Validate a persisted artifact directory and report actionable violations",
    )
    validate.add_argument("artifact", type=Path, help="Persisted AKILAN artifact directory")
    return parser


def _run_extract(args: argparse.Namespace) -> int:
    config = _config_from_args(args, overwrite=args.overwrite)
    artifact = PDFArtifactBuilder(config).build(
        args.pdf,
        args.output,
        password=_password_from_args(args),
    )
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


def _run_validate(args: argparse.Namespace) -> int:
    artifact_dir = args.artifact.expanduser().resolve()
    try:
        document = load_artifact_directory(artifact_dir)
    except ArtifactSchemaError as exc:
        print(
            json.dumps(
                {
                    "artifact": str(artifact_dir),
                    "valid": False,
                    "violation_count": len(exc.violations),
                    "violations": [
                        {"path": violation.path, "message": violation.message}
                        for violation in exc.violations
                    ],
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    statistics = document.get("statistics", {})
    print(
        json.dumps(
            {
                "artifact": str(artifact_dir),
                "valid": True,
                "schema_version": document.get("schema_version"),
                "pages": statistics.get("page_count", len(document.get("pages", []))),
                "violation_count": 0,
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "extract":
        return _run_extract(args)
    if args.command == "benchmark":
        return _run_benchmark(args)
    if args.command == "validate":
        return _run_validate(args)
    return 2
