import json
from pathlib import Path

from akilan import PdfPageParser, PdfPageRenderer


def main():
    pdf_path = "data/2024-wttc-introduction-to-ai.pdf"
    page_number = 18

    parser = PdfPageParser(pdf_path=pdf_path)
    renderer = PdfPageRenderer(pdf_path=pdf_path)

    page = parser.parse_page(
        page_number=page_number,
        include_table_base64=True,
        include_image_base64=True,
        skip_background_images=True,
        enable_grouping=True,
    )

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / f"page_{page_number}.json"
    overlay_path = output_dir / f"page_{page_number}_overlay.png"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(page.to_dict(), f, indent=2, ensure_ascii=False)

    renderer.render_page_with_bboxes(
        page_data=page,
        output_path=overlay_path,
        zoom=2.0,
        show_labels=True,
        recurse_groups=True,
    )

    print(f"Saved JSON to {json_path}")
    print(f"Saved overlay to {overlay_path}")
    print(page.debug)


if __name__ == "__main__":
    main()
