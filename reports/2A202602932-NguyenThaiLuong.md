# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Thái Lương
- Mã học viên: 2A202602932
- Nhóm: FourBro
- Repository/branch: thailuong1008-coder/K4-Day08-FourBro / main

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 5 — Semantic Search | Implement `semantic_search()`: embed query bằng `embed_texts()`, truy vấn ChromaDB qua `get_collection()`, chuyển cosine distance sang cosine similarity `max(0.0, 1.0 - distance)`, sort giảm dần theo score và giới hạn `top_k`, gán `retrieval_method="dense"` | `src/task5_semantic_search.py` | Done |
| Task 6 — Lexical Search | Implement `build_bm25_index()` + `lexical_search()`: dựng BM25 index từ corpus chunks bằng `BM25Plus`, tokenize query và corpus, tính điểm BM25, sort và trả về `SearchResult` với `retrieval_method="bm25"` | `src/task6_lexical_search.py` | Done |
| Task 7 — RRF Reranking | Implement `rerank_rrf()`: thuật toán Reciprocal Rank Fusion kết hợp thứ hạng từ nhiều danh sách (dense + sparse) với công thức $RRF(d) = \sum 1/(k + rank)$, $k=60$. Khử trùng lặp ID, gán `retrieval_method="hybrid"` | `src/task7_reranking.py` | Done |
| Task 9 — Retrieval Pipeline | Implement `retrieve()`: pipeline tích hợp chạy semantic và lexical search, fuse kết quả bằng RRF đúng một lần. Kiểm tra `best_dense_score` với `score_threshold` (0.35) để kích hoạt fallback sang `pageindex_search()`. Xử lý exception bảo đảm pipeline không crash | `src/task9_retrieval_pipeline.py` | Done |
| Phân công & Architecture Docs | Cập nhật `README.md` chuẩn hóa bảng phân công 4 roles của nhóm, tài liệu hóa toàn bộ kiến trúc Hybrid Retrieval Pipeline, tiêu chuẩn hợp đồng `SearchResult` và checklist nghiệm thu của TV2 | `README.md`, commit `1c95211` | Done |
| Repository & Branch Integration | Đồng bộ repository, tích hợp PR #2 (`hoanganh`) vào `main`, bảo đảm toàn bộ mã nguồn và dữ liệu chuẩn hóa của nhóm hoạt động thống nhất | PR #2, commit `d110eb3` | Done |

Chỉ kê khai công việc có thể đối chiếu bằng file, commit, pull request, test hoặc kết quả evaluation.

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định:** Sử dụng thuật toán Reciprocal Rank Fusion (RRF với $k=60$) thay vì Weighted Sum Fusion (kết hợp tuyến tính điểm số) giữa Dense Search và BM25.  
   **Lý do/evidence:** Thang điểm Cosine Similarity $\in [0, 1]$ trong khi điểm BM25 không có chặn trên và phụ thuộc lớn vào độ dài văn bản cùng tần suất từ (IDF). Việc chuẩn hóa Min-Max rất nhạy cảm với outlier và query ngắn. RRF dựa hoàn toàn trên vị trí thứ hạng (rank), giúp loại bỏ hoàn toàn sự lệch thang đo và mang lại tính ổn định cao.  
   **Trade-off:** Mất đi thông tin về khoảng cách độ tương đồng tương đối giữa các document kề nhau trên bảng xếp hạng (khoảng cách điểm giữa rank 1 và rank 2 bị cố định theo hàm $\frac{1}{60 + rank}$).

2. **Quyết định:** Quyết định kích hoạt Fallback sang PageIndex dựa trên Cosine Similarity gốc của Dense Search thay vì điểm sau khi tính RRF.  
   **Lý do/evidence:** Điểm RRF chỉ phản ánh độ đồng thuận thứ tự giữa các phương pháp retrieve trong tập ứng viên, không phản ánh mức độ tin cậy tuyệt đối của tài liệu đối với câu hỏi. Cosine Similarity gốc từ embedding phản ánh trực tiếp ngữ nghĩa: khi điểm dense cao nhất $< 0.35$, câu hỏi nhiều khả năng nằm ngoài miền dữ liệu (out-of-domain) hoặc mang tính tổng quan cấu trúc, cần fallback sang PageIndex.  
   **Trade-off:** Phải lưu vết và truyền song song giá trị điểm Dense gốc cùng kết quả tìm kiếm trước khi thực hiện bước fuse RRF.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng:
  - `pytest tests/test_contracts.py -k "semantic or lexical or rrf or retrieve" -v` → 6/6 tests passed (100% pass)
  - `pytest tests/test_contracts.py -k "test_public_function_signatures_are_stable" -v` → passed
  - Query kiểm tra phân ngưỡng threshold:
    - In-domain: *"Quy chế tuyển sinh đại học Bách khoa Hà Nội 2024"*, *"Phương thức xét tuyển tài năng XTTN"* (Dense score $\ge 0.60$)
    - Out-of-domain: *"Chính sách bảo hành sản phẩm điện tử"*, *"Thời tiết hôm nay"* (Dense score $< 0.30 \rightarrow$ kích hoạt fallback)
- Kết quả trước/sau nếu có:
  - Trước: Các file `task5`, `task6`, `task7`, `task9` ném `NotImplementedError`, fail toàn bộ các test contract của retrieval.
  - Sau: Toàn bộ pipeline tìm kiếm chạy mượt mà, trả kết quả chuẩn format `SearchResult`, vượt qua 100% các ràng buộc kiểm thử.
- Lỗi đã phát hiện và cách xử lý:
  - Lỗi Zero IDF với `BM25Okapi`: Khi test trên corpus mẫu 2 chunks, công thức Robertson IDF cho ra $\ln(1) = 0$, khiến điểm BM25 = 0 và bị lọc mất. Đã xử lý bằng cách chuyển sang `BM25Plus` trong package `rank_bm25` để bảo đảm từ khóa khớp luôn nhận điểm dương.
  - Lỗi tiềm ẩn khi Fallback provider gặp sự cố mạng/ngoại lệ: Đã bọc khối `try...except` quanh `pageindex_search()`, nếu fallback lỗi thì tự động trả về kết quả `hybrid` an toàn thay vì làm gián đoạn chatbot.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Tokenizer cho BM25 hiện tại đang sử dụng tách từ theo khoảng trắng `split()`, chưa sử dụng thư viện tách từ ghép tiếng Việt chuyên dụng (như `pyvi` hoặc `underthesea`), làm giảm độ chính xác khi tìm cụm từ ghép đặc thù.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tích hợp bộ tiền xử lý tokenizer tiếng Việt chuyên biệt cho BM25 và thử nghiệm thêm Cross-Encoder Reranker (`BAAI/bge-reranker-large`) sau bước RRF để nâng cao hơn nữa Context Precision.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-25
- Tên thành viên: Nguyễn Thái Lương
