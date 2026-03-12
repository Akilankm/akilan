from rich import print
from akilan.text_extraction import PdfTextExtractor

extractor = PdfTextExtractor("data/2024-wttc-introduction-to-ai.pdf")
blocks = extractor.extract_page_blocks(10)
print(blocks)