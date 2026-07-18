from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pytest

from akilan.cli import _password_from_args, build_parser


def _args(
    *,
    password: str | None = None,
    password_file: Path | None = None,
    password_stdin: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        password=password,
        password_file=password_file,
        password_stdin=password_stdin,
    )


def test_password_file_removes_only_one_terminal_line_ending(tmp_path: Path) -> None:
    password_file = tmp_path / "password.txt"
    password_file.write_text("  secret value  \r\n", encoding="utf-8")

    assert _password_from_args(_args(password_file=password_file)) == "  secret value  "


def test_password_stdin_reads_exactly_one_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("first-secret\nsecond-secret\n"))

    assert _password_from_args(_args(password_stdin=True)) == "first-secret"
    assert sys.stdin.readline() == "second-secret\n"


def test_empty_password_sources_fail_without_starting_extraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password_file = tmp_path / "empty.txt"
    password_file.write_text("", encoding="utf-8")

    with pytest.raises(SystemExit, match="password file is empty"):
        _password_from_args(_args(password_file=password_file))

    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    with pytest.raises(SystemExit, match="no password was received"):
        _password_from_args(_args(password_stdin=True))


def test_missing_password_file_reports_actionable_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"

    with pytest.raises(SystemExit, match="cannot read password file"):
        _password_from_args(_args(password_file=missing))


def test_password_sources_are_mutually_exclusive() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "extract",
                "document.pdf",
                "--output",
                "artifact",
                "--password",
                "secret",
                "--password-stdin",
            ]
        )
