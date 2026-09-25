"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from pageindex import PageIndexAPIError, PageIndexClient


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
LANDING_LEGAL_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
DOC_ID_CACHE = Path(__file__).parent.parent / "data" / "pageindex_doc_ids.json"

POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 300


def _client() -> PageIndexClient:
    if not PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY is not set")
    return PageIndexClient(PAGEINDEX_API_KEY)


def _load_cache() -> dict[str, str]:
    """source filename -> PageIndex doc_id."""
    if DOC_ID_CACHE.exists():
        return json.loads(DOC_ID_CACHE.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    DOC_ID_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DOC_ID_CACHE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _wait_until_ready(client: PageIndexClient, doc_id: str) -> bool:
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    while time.time() < deadline:
        if client.is_retrieval_ready(doc_id):
            return True
        time.sleep(POLL_INTERVAL_SECONDS)
    return False


def upload_documents() -> None:
    """Upload PDF pháp lý lên PageIndex và cache mapping source -> doc_id.

    PageIndex chỉ nhận PDF. Nếu nhóm chỉ có DOCX, convert sang PDF trước
    (ví dụ dùng LibreOffice/docx2pdf) rồi đặt file .pdf vào cùng thư mục.
    """
    client = _client()
    cache = _load_cache()

    pdf_paths = sorted(LANDING_LEGAL_DIR.glob("*.pdf"))
    if not pdf_paths:
        print(f"Không tìm thấy PDF trong {LANDING_LEGAL_DIR}")
        return

    for path in pdf_paths:
        source = path.name
        if source in cache:
            print(f"Bỏ qua {source}: đã upload trước đó ({cache[source]})")
            continue

        response = client.submit_document(str(path))
        doc_id = response["doc_id"]
        cache[source] = doc_id
        _save_cache(cache)  # lưu ngay để không mất mapping nếu bước sau lỗi
        print(f"Đã upload {source} -> {doc_id}, đang chờ xử lý...")

        if _wait_until_ready(client, doc_id):
            print(f"{source} đã sẵn sàng để retrieval")
        else:
            print(
                f"{source} vẫn đang xử lý sau {POLL_TIMEOUT_SECONDS}s; "
                "kiểm tra lại bằng client.get_tree(doc_id) sau."
            )


def _poll_retrieval(client: PageIndexClient, retrieval_id: str) -> dict:
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    while time.time() < deadline:
        payload = client.get_retrieval(retrieval_id)
        status = payload.get("status")
        if status in ("completed", "done", "ready"):
            return payload
        if status == "failed":
            raise PageIndexAPIError(f"retrieval {retrieval_id} failed")
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"retrieval {retrieval_id} timed out")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Query mọi document đã cache và trả về pageindex SearchResult.

    Gọi hàm này an toàn: mọi lỗi cục bộ (network, timeout, doc lỗi) chỉ bỏ
    qua document đó thay vì làm crash toàn bộ pipeline. Task 9 vẫn nên bọc
    lệnh gọi bằng try/except vì đây là service ngoài.
    """
    cache = _load_cache()
    if not cache:
        return []

    client = _client()
    results: list[dict] = []

    for source, doc_id in cache.items():
        try:
            submission = client.submit_query(doc_id, query)
            payload = _poll_retrieval(client, submission["retrieval_id"])
        except (PageIndexAPIError, KeyError, TimeoutError):
            continue

        # NOTE: kiểm tra response thật của SDK — field có thể là "results"
        # hoặc "nodes" tuỳ version; điều chỉnh nếu khác.
        nodes = payload.get("results") or payload.get("nodes") or []
        for rank, node in enumerate(nodes, start=1):
            content = node.get("text") or node.get("content") or ""
            if not content.strip():
                continue
            score = node.get("score")
            if not isinstance(score, (int, float)):
                score = 1.0 / rank  # API không trả score -> giảm dần theo rank
            results.append(
                {
                    "id": f"{source}::pageindex-{node.get('node_id', rank)}",
                    "content": content,
                    "score": float(score),
                    "metadata": {
                        "source": source,
                        "title": Path(source).stem,
                        "doc_type": "legal",
                        "url": None,
                        "chunk_index": rank - 1,
                    },
                    "retrieval_method": "pageindex",
                }
            )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    upload_documents()