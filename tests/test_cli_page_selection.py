from __future__ import annotations

import pytest

from akilan.cli import _config_from_args, build_parser


def test_extract_cli_page_selection_populates_config() -> None:
    args = build_parser().parse_args(
        [
            "extract",
            "document.pdf",
            "--output",
            "artifact",
            "--pages",
            "1,3-5,9",
        ]
    )

    config = _config_from_args(args, overwrite=args.overwrite)

    assert config.page_numbers == (1, 3, 4, 5, 9)


def test_benchmark_cli_page_selection_populates_config() -> None:
    args = build_parser().parse_args(
        [
            "benchmark",
            "corpus",
            "--output-root",
            "artifacts",
            "--report",
            "report.json",
            "--pages",
            "2-4",
        ]
    )

    config = _config_from_args(args, overwrite=True)

    assert config.page_numbers == (2, 3, 4)


@pytest.mark.parametrize("expression", ["", "0", "3-1", "1,1", "2,1", "1-"])
def test_cli_rejects_invalid_page_selection_with_actionable_error(expression: str) -> None:
    args = build_parser().parse_args(
        [
            "extract",
            "document.pdf",
            "--output",
            "artifact",
            "--pages",
            expression,
        ]
    )

    with pytest.raises(SystemExit, match="invalid page selection"):
        _config_from_args(args, overwrite=args.overwrite)


def test_cli_without_page_selection_preserves_full_document_default() -> None:
    args = build_parser().parse_args(
        ["extract", "document.pdf", "--output", "artifact"]
    )

    config = _config_from_args(args, overwrite=args.overwrite)

    assert config.page_numbers is None
