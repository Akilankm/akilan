from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_notebook_contract.py"
_SPEC = importlib.util.spec_from_file_location("validate_notebook_contract", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def _write_notebook(path: Path, *, outputs: list[dict[str, object]] | None = None) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "markdown", "metadata": {}, "source": ["# Demo"]},
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "metadata": {},
                        "outputs": outputs or [],
                        "source": ["print('ok')"],
                    },
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )


def test_validate_notebook_accepts_well_formed_notebook(tmp_path: Path) -> None:
    notebook = tmp_path / "demo.ipynb"
    _write_notebook(notebook)

    evidence = _MODULE.validate_notebook(notebook)

    assert evidence["valid"] is True
    assert evidence["code_cell_count"] == 1
    assert evidence["has_error_outputs"] is False


def test_validate_notebook_rejects_error_output(tmp_path: Path) -> None:
    notebook = tmp_path / "demo.ipynb"
    _write_notebook(
        notebook,
        outputs=[{"output_type": "error", "ename": "RuntimeError", "evalue": "boom", "traceback": []}],
    )

    try:
        _MODULE.validate_notebook(notebook)
    except _MODULE.NotebookContractError as exc:
        assert "error outputs" in str(exc)
    else:
        raise AssertionError("expected notebook contract failure")


def test_require_outputs_fails_for_unrendered_notebook(tmp_path: Path) -> None:
    notebook = tmp_path / "demo.ipynb"
    _write_notebook(notebook)

    try:
        _MODULE.validate_notebook(notebook, require_outputs=True)
    except _MODULE.NotebookContractError as exc:
        assert "at least one code-cell output" in str(exc)
    else:
        raise AssertionError("expected rendered-output contract failure")
