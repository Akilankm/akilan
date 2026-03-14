import json
from pathlib import Path

from akilan import PdfPageParser


def main():
    pdf_path = "data/2024-wttc-introduction-to-ai.pdf"
    page_number = 31

    parser = PdfPageParser(pdf_path=pdf_path)

    page = parser.parse_page(
        page_number=page_number,
        include_table_base64=True,
        include_image_base64=True,
        skip_background_images=True,
        enable_grouping=True,
    )

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"page_{page_number}.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(page.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"Saved page {page_number} to {output_file}")
    print(json.dumps(page.to_dict(), indent=2, ensure_ascii=False)[:7000])


if __name__ == "__main__":
    main()