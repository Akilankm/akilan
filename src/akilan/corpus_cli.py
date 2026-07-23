"""Operational CLI for synchronizing and verifying the declared public PDF corpus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .corpus import CorpusSourceError, sync_corpus, verify_corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="akilan-corpus", description="Manage AKILAN's declared public PDF corpus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser("sync", help="Download and validate every declared PDF")
    sync.add_argument("manifest", type=Path)
    sync.add_argument("--data-dir", type=Path, default=Path("data"))
    sync.add_argument("--overwrite", action="store_true")
    sync.add_argument("--timeout", type=float, default=30.0)
    sync.add_argument("--max-bytes", type=int, default=50 * 1024 * 1024)

    verify = subparsers.add_parser("verify", help="Validate declared local PDFs without network access")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("--data-dir", type=Path, default=Path("data"))
    return parser


def _run_sync(args: argparse.Namespace) -> int:
    try:
        results = sync_corpus(
            args.manifest,
            args.data_dir,
            overwrite=args.overwrite,
            timeout_seconds=args.timeout,
            max_bytes=args.max_bytes,
        )
    except (CorpusSourceError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "sources": [
                    {
                        "id": result.source_id,
                        "status": result.status,
                        "path": str(result.path),
                        "sha256": result.sha256,
                        "size_bytes": result.size_bytes,
                        "page_count": result.page_count,
                    }
                    for result in results
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _run_verify(args: argparse.Namespace) -> int:
    try:
        results = verify_corpus(args.manifest, args.data_dir)
    except CorpusSourceError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    valid = all(result.valid for result in results)
    payload = {
        "ok": valid,
        "sources": [
            {
                "id": result.source_id,
                "status": result.status,
                "path": str(result.path),
                "expected_sha256": result.expected_sha256,
                "actual_sha256": result.actual_sha256,
                "size_bytes": result.size_bytes,
                "page_count": result.page_count,
                "message": result.message,
            }
            for result in results
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stdout if valid else sys.stderr)
    return 0 if valid else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "sync":
        return _run_sync(args)
    if args.command == "verify":
        return _run_verify(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
