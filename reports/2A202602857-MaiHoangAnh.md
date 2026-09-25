
## Thông tin

- Họ và tên: Mai Hoàng Anh
- Mã học viên: 2A202602857
- Nhóm: FourBro
- Repository/branch: K4-L3B-RAG-Pipeline / main

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1 — Thu thập tài liệu pháp lý | Implement `download_documents()`: đọc `data/sources.json`, tải 3 PDF từ HUST qua `requests`, lưu kèm metadata JSON, skip nếu đã tồn tại | `src/task1_collect_legal_docs.py` | Done |
| Task 2 — Crawl bài viết | Implement `crawl_article()` + `crawl_all()`: crawl 5 bài từ HUST bằng `requests` + `BeautifulSoup` + `markdownify`, lưu JSON với schema chuẩn (`url`, `title`, `date_crawled`, `content_markdown`) | `src/task2_crawl_news.py` | Done |
| Task 3 — Chuẩn hóa Markdown | Implement `convert_legal_docs()` + `convert_news_articles()`: convert 3 PDF bằng MarkItDown, convert 5 JSON news thành Markdown với metadata header, lưu vào `data/standardized/` | `src/task3_convert_markdown.py` | Done |
| Task 4 — Chunking + Embedding + Indexing | Implement toàn bộ pipeline: `load_documents()`, `chunk_documents()`, `embed_texts()`, `embed_chunks()`, `get_collection()`, `index_to_vectorstore()`. Hỗ trợ multi-provider embedding (OpenAI/SentenceTransformers/Gemini). Upsert 1.135 chunks vào ChromaDB | `src/task4_chunking_indexing.py` | Done |
| Cấu hình embedding | Chuyển `EMBEDDING_PROVIDER` từ `sentence_transformers` (chưa cài) sang `openai` (`text-embedding-3-small`) | `.env` | Done |

Chỉ kê khai công việc có thể đối chiếu bằng file, commit, pull request, test hoặc kết quả evaluation.

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định:** Chuyển embedding provider từ `sentence_transformers` (BAAI/bge-m3) sang OpenAI API (`text-embedding-3-small`).  
   **Lý do/evidence:** Package `sentence-transformers` bị comment trong `pyproject.toml` và chưa cài đặt. OpenAI API đã có key sẵn trong `.env`, không cần tải model ~2GB, embed nhanh hơn.  
   **Trade-off:** Phụ thuộc API bên ngoài (cần mạng + tốn credit), nhưng đổi lại triển khai nhanh và không cần GPU local. Code vẫn hỗ trợ đổi về `sentence_transformers` qua `.env` nếu cần.

2. **Quyết định:** Dùng `requests` + `BeautifulSoup` + `markdownify` cho Task 2 thay vì `crawl4ai` (yêu cầu Playwright + headless browser).  
   **Lý do/evidence:** Các trang HUST là static HTML, không cần JavaScript rendering. `requests` nhẹ hơn, nhanh hơn, ít dependency hơn.  
   **Trade-off:** Không hỗ trợ trang SPA/JS-rendered, nhưng với nguồn dữ liệu hiện tại thì đủ dùng. Nếu cần crawl trang phức tạp hơn, có thể quay lại `crawl4ai`.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `python -m src.task1_collect_legal_docs` → 3/3 PDF ready (skip vì đã tồn tại)
  - `python -m src.task2_crawl_news` → 5/5 JSON ready (skip vì đã tồn tại)
  - `python -m src.task3_convert_markdown` → 8 Markdown files (3 legal + 5 news)
  - `python -m src.task4_chunking_indexing` → 1.135 chunks indexed, all IDs unique, all metadata valid
  - `pytest tests/test_contracts.py -q` → 11 passed (tất cả tests liên quan Task 1–4), 7 failed (thuộc Task 5–10 chưa implement)
- Kết quả trước/sau nếu có:
  - Trước: Tất cả 4 task đều `raise NotImplementedError`
  - Sau: Pipeline hoàn chỉnh từ thu thập → chuẩn hóa → chunking → embedding → ChromaDB index
- Lỗi đã phát hiện và cách xử lý:
  - `UnicodeEncodeError` khi print ký tự `✓` trên Windows cp1252 → thay bằng `[OK]`
  - Task 2 import module `config` và `ingestion` không tồn tại → rewrite self-contained

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Chunk size cố định 500 chars chưa được tối ưu cho tiếng Việt; một số bảng/hình ảnh trong PDF có thể bị mất format khi convert qua MarkItDown.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Thử nghiệm semantic chunking hoặc chunk theo heading thay vì fixed-size, và so sánh retrieval quality giữa các strategy.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-25
- Tên thành viên: Mai Hoàng Anh
