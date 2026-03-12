# AKILAN

**Adaptive Knowledge Ingestion Layer for Analytics Nodes**

AKILAN is a lightweight Python library built on top of **PyMuPDF** for structured PDF text extraction.
It provides clean APIs to extract text **block-by-block** or **page-by-page** while preserving layout order.

The library is designed for **AI pipelines, document processing, and Retrieval-Augmented Generation (RAG) workflows**.

---

## Features

* Extract **structured text blocks** from PDFs
* Preserve **top-to-bottom reading order**
* Access **bounding box coordinates** for layout-aware processing
* Lightweight wrapper around **PyMuPDF**
* Designed for **AI-ready document ingestion pipelines**

---

## Installation

```bash
pip install akilan
```

---

## Quick Example

```python
from akilan import PdfTextExtractor

extractor = PdfTextExtractor("document.pdf")

blocks = extractor.extract_page_blocks(1)

for block in blocks:
    print(block["text"])
```

---

## Extract Plain Page Text

```python
text = extractor.extract_page_text(1)
print(text)
```

---

## Example Output

```python
[
  {
    "block_index": 0,
    "page_number": 1,
    "bbox": {"x0": 72.0, "y0": 54.1, "x1": 410.3, "y1": 88.7},
    "text": "Introduction to PDF Extraction"
  },
  {
    "block_index": 1,
    "page_number": 1,
    "bbox": {"x0": 72.0, "y0": 102.0, "x1": 500.1, "y1": 180.2},
    "text": "This document explains how text can be extracted from structured PDFs."
  }
]
```

---

## How It Works

```
PDF Document
      ↓
PyMuPDF Parser
      ↓
AKILAN Extraction Layer
      ↓
Structured Blocks / Page Text
      ↓
AI Pipelines / RAG / Analytics
```

---

## Use Cases

AKILAN works well for:

* AI document ingestion pipelines
* Retrieval-Augmented Generation (RAG)
* PDF preprocessing for LLMs
* Document analytics
* Structured content extraction

---

## Project Structure

```
akilan
├── src/akilan
│   ├── text_extraction.py
│   └── logger.py
```

---

## License

MIT License

---

## Author

Akilan
