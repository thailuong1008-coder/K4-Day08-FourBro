"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

import json
from pathlib import Path

from markitdown import MarkItDown

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs() -> None:
    """Convert PDF/DOCX từ landing/legal sang standardized/legal.

    Dùng MarkItDown để trích xuất text từ PDF/DOCX.
    Thêm metadata header (title, source URL) ở đầu file Markdown.
    Bỏ qua nếu file output đã tồn tại hoặc nội dung rỗng.
    """
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = MarkItDown()
    converted = 0

    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue

        out_path = output_dir / f"{path.stem}.md"
        if out_path.exists():
            print(f"  Skipped (exists): {out_path.name}")
            converted += 1
            continue

        # Đọc metadata nếu có
        meta_path = legal_dir / f"{path.stem}.metadata.json"
        title = path.stem
        url = None
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            title = meta.get("title", path.stem)
            url = meta.get("url")

        print(f"  Converting: {path.name} ...")
        result = converter.convert(str(path))
        content = result.text_content.strip() if result.text_content else ""

        if not content:
            print(f"  Warning: empty content from {path.name}, skipping")
            continue

        # Tạo Markdown với metadata header
        header = f"# {title}\n\n"
        if url:
            header += f"**Source:** {url}\n\n"
        header += f"**File:** {path.name}\n\n---\n\n"

        out_path.write_text(header + content, encoding="utf-8")
        converted += 1
        print(f"  Saved: {out_path.name} ({len(content):,} chars)")

    print(f"  Legal: {converted} documents converted.")


def convert_news_articles() -> None:
    """Convert JSON từ landing/news sang standardized/news.

    Giữ metadata (title, source URL, date_crawled) ở header.
    Bỏ qua nếu file output đã tồn tại hoặc nội dung rỗng.
    """
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    converted = 0

    for path in sorted(news_dir.glob("*.json")):
        out_path = output_dir / f"{path.stem}.md"
        if out_path.exists():
            print(f"  Skipped (exists): {out_path.name}")
            converted += 1
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        content_md = data.get("content_markdown", "").strip()

        if not content_md:
            print(f"  Warning: empty content in {path.name}, skipping")
            continue

        header = (
            f"# {data.get('title', path.stem)}\n\n"
            f"**Source:** {data.get('url', 'N/A')}\n\n"
            f"**Crawled:** {data.get('date_crawled', 'N/A')}\n\n---\n\n"
        )

        out_path.write_text(header + content_md, encoding="utf-8")
        converted += 1
        print(f"  Saved: {out_path.name} ({len(content_md):,} chars)")

    print(f"  News: {converted} articles converted.")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Converting legal documents...")
    convert_legal_docs()
    print("Converting news articles...")
    convert_news_articles()
    print(f"\nSaved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()