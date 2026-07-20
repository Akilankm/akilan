# Notebook validation contract

`notebooks/pdf_artifact_workbench.ipynb` is a user-facing executable artifact. Its committed JSON must remain structurally valid and must never contain saved Python error outputs.

Validate it without adding `nbformat` or Jupyter to runtime dependencies:

```bash
python scripts/validate_notebook_contract.py \
  notebooks/pdf_artifact_workbench.ipynb \
  --report artifacts/notebook-contract.json
```

Use `--require-outputs` only for a notebook that is intentionally committed with rendered results. The current workbench may remain unexecuted because it downloads public corpus files and writes artifacts in the local environment.

The validator fails closed for unreadable JSON, unsupported notebook format, empty or malformed cells, missing cell sources, malformed code-cell outputs, saved error outputs, and missing rendered output when explicitly required. It emits deterministic machine-readable evidence and uses only the Python standard library.
