#!/usr/bin/env python3
"""Validate the committed AKILAN workbench notebook without extra dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class NotebookContractError(ValueError):
    """Raised when a notebook violates the repository contract."""


def validate_notebook(path: Path, *, require_outputs: bool = False) -> dict[str, Any]:
    """Validate notebook structure and return deterministic evidence."""

    path = path.expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NotebookContractError(f"unreadable notebook: {exc}") from exc

    if payload.get("nbformat") != 4:
        raise NotebookContractError("nbformat must be 4")
    cells = payload.get("cells")
    if not isinstance(cells, list) or not cells:
        raise NotebookContractError("cells must be a non-empty list")

    code_cells = 0
    output_cells = 0
    error_outputs: list[int] = []
    missing_sources: list[int] = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            raise NotebookContractError(f"cell {index} must be an object")
        source = cell.get("source")
        if not isinstance(source, list) or not source:
            missing_sources.append(index)
        if cell.get("cell_type") != "code":
            continue
        code_cells += 1
        outputs = cell.get("outputs")
        if not isinstance(outputs, list):
            raise NotebookContractError(f"code cell {index} outputs must be a list")
        if outputs:
            output_cells += 1
        for output in outputs:
            if isinstance(output, dict) and output.get("output_type") == "error":
                error_outputs.append(index)

    if missing_sources:
        raise NotebookContractError(f"cells without source: {missing_sources}")
    if code_cells == 0:
        raise NotebookContractError("notebook must contain at least one code cell")
    if error_outputs:
        raise NotebookContractError(f"error outputs in code cells: {sorted(set(error_outputs))}")
    if require_outputs and output_cells == 0:
        raise NotebookContractError("rendered notebook must contain at least one code-cell output")

    return {
        "contract_version": "notebook-contract-v1",
        "path": str(path),
        "cell_count": len(cells),
        "code_cell_count": code_cells,
        "code_cells_with_outputs": output_cells,
        "has_error_outputs": False,
        "valid": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--require-outputs", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    try:
        evidence = validate_notebook(args.notebook, require_outputs=args.require_outputs)
    except NotebookContractError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1

    rendered = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if args.report is not None:
        report = args.report.expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
