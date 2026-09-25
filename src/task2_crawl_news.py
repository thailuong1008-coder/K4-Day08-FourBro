"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"
SOURCES_FILE = Path(__file__).parent.parent / "data" / "sources.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def _load_news_sources() -> list[dict]:
    """Đọc danh sách bài viết từ data/sources.json."""
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    news_sources = sources.get("news", [])
    if len(news_sources) < 5:
        raise ValueError(
            f"Cần tối thiểu 5 bài viết news, chỉ tìm thấy {len(news_sources)} "
            f"trong {SOURCES_FILE}"
        )
    return news_sources


def parse_article(html: bytes, url: str) -> dict:
    """Parse HTML thành dict với schema chuẩn."""
    soup = BeautifulSoup(html, "html.parser")

    # Tìm title
    title_tag = soup.find("h1") or soup.find("title")
    if title_tag is None:
        raise ValueError("Không tìm thấy title trong trang")
    title = title_tag.get_text(" ", strip=True)

    # Tìm body content — thử nhiều selector phổ biến
    body = (
        soup.select_one("#bodytext")
        or soup.select_one("#news-bodyhtml")
        or soup.select_one(".news-bodyhtml")
        or soup.select_one(".post-content")
        or soup.select_one(".entry-content")
        or soup.find("article")
        or soup.find("main")
    )
    if body is None:
        # Fallback: dùng toàn bộ body
        body = soup.find("body")
    if body is None:
        raise ValueError("Không tìm thấy nội dung bài viết")

    # Loại bỏ các tag không cần thiết
    for tag in body.select("script, style, nav, form, iframe, header, footer"):
        tag.decompose()

    content = markdownify(str(body), heading_style="ATX").strip()
    if len(content) < 100:
        raise ValueError(f"Nội dung quá ngắn ({len(content)} ký tự)")

    sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256,
        "content_markdown": content,
    }


async def crawl_article(url: str) -> dict:
    """Tải và parse một bài viết."""
    response = await asyncio.to_thread(
        requests.get, url, headers=HEADERS, timeout=60
    )
    response.raise_for_status()
    return parse_article(response.content, response.url)


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    news_sources = _load_news_sources()
    saved_count = 0
    failures = []

    for source in news_sources:
        url = source["url"]
        filename = source["filename"]
        output = DATA_DIR / filename

        # Bỏ qua nếu file đã tồn tại
        if output.exists():
            print(f"Skipped (exists): {output.name}")
            saved_count += 1
            continue

        try:
            article = await crawl_article(url)
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            saved_count += 1
            print(f"Saved: {filename} ({len(article['content_markdown'])} chars)")
        except Exception as error:
            failures.append(f"{filename}: {type(error).__name__}: {error}")
            print(f"Failed: {url} — {error}")

    print(f"\nTotal: {saved_count}/{len(news_sources)} news articles ready.")
    if failures:
        print("Failures:")
        for f in failures:
            print(f"  - {f}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
