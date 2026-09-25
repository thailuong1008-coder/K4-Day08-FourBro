"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
SOURCES_FILE = Path(__file__).parent.parent / "data" / "sources.json"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai.

    Đọc danh sách tài liệu từ data/sources.json, tải từng file PDF
    và lưu kèm metadata JSON. Bỏ qua file đã tồn tại.
    """
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    legal_sources = sources.get("legal", [])

    if len(legal_sources) < 3:
        raise ValueError(
            f"Cần tối thiểu 3 tài liệu legal, chỉ tìm thấy {len(legal_sources)} "
            f"trong {SOURCES_FILE}"
        )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    downloaded = 0
    for item in legal_sources:
        filename = item["filename"]
        url = item["url"]
        title = item.get("title", filename)
        dest = DATA_DIR / filename

        # Bỏ qua nếu file đã tồn tại
        if dest.exists():
            print(f"Skipped (exists): {dest.name}")
            downloaded += 1
            continue

        print(f"Downloading: {url}")
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        dest.write_bytes(response.content)
        sha256 = hashlib.sha256(response.content).hexdigest()

        # Lưu metadata
        meta = {
            "filename": filename,
            "title": title,
            "url": url,
            "date_crawled": datetime.now(timezone.utc).isoformat(),
            "sha256": sha256,
            "doc_type": "legal",
            "source": f"legal/{filename}",
        }
        meta_path = DATA_DIR / f"{Path(filename).stem}.metadata.json"
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        downloaded += 1
        print(f"Saved: {dest.name} ({len(response.content):,} bytes)")

    print(f"\nTotal: {downloaded}/{len(legal_sources)} legal documents ready.")


if __name__ == "__main__":
    setup_directory()
    download_documents()
