# Day 8 — RAG Pipeline: Hệ thống Tư vấn Tuyển sinh & Quy chế Đào tạo ĐHBK Hà Nội (HUST)

> **Nhóm thực hiện**: FourBro (`K4-Day08-FourBro`)  
> **Chủ đề**: Chatbot RAG hỗ trợ tra cứu thông tin tuyển sinh, quy chế đào tạo, điểm chuẩn và đề án đào tạo Đại học Bách khoa Hà Nội (HUST).

---

## 👥 Bảng phân công nhiệm vụ nhóm (Team Roles)

| Thành viên | Vai trò | Nhiệm vụ chính phụ trách | Trạng thái |
| :--- | :--- | :--- | :---: |
| **Thành viên 1** | **Data Engineer** | Phụ trách thu thập và chuẩn hóa dữ liệu. Thu thập tối thiểu 3 tài liệu PDF/DOCX và 5 trang/bài viết có nguồn rõ ràng, chuyển đổi dữ liệu sang Markdown, làm sạch dữ liệu và thực hiện chunking. Bảo đảm dữ liệu có metadata đầy đủ, ID ổn định, chunk không rỗng và sẵn sàng cho bước embedding và retrieval. | Hoàn thành |
| **Thành viên 2** | **Retrieval Engineer** | **Phụ trách toàn bộ hệ thống tìm kiếm**. Thực hiện embedding, lưu trữ trên ChromaDB, xây dựng Dense Search, BM25 Lexical Search, Reciprocal Rank Fusion (RRF) và retrieval pipeline. Thực hiện calibrate threshold, xây dựng fallback và kiểm tra các yêu cầu về `SearchResult`, `top_k`, `score`, `id` và công thức RRF theo contract. | **Hoàn thành** |
| **Thành viên 3** | **Generation / RAG Engineer** | Phụ trách phần xử lý sau retrieval và sinh câu trả lời. Xây dựng PageIndex/fallback provider, reorder chunks, format context, kết nối LLM, sinh câu trả lời có citation và xây dựng cơ chế safe refusal khi hệ thống không có đủ bằng chứng. Đảm bảo citation truy xuất được về đúng nguồn trong sources và không tự suy diễn ngoài dữ liệu. | Đang tích hợp |
| **Thành viên 4** | **Product & Evaluation Engineer** | Phụ trách chatbot và đánh giá hệ thống. Hoàn thiện giao diện Streamlit, hiển thị câu trả lời, nguồn, retrieval method và score; xây dựng tối thiểu 15 câu Golden Q&A; chạy 4 metric gồm Faithfulness, Answer Relevance, Context Recall và Context Precision; thực hiện A/B giữa Dense-only và Hybrid + RRF; phân tích lỗi và hoàn thiện `RESULT.md`. | Đang tích hợp |

---

## 🔍 Kiến trúc & Đặc tả Kỹ thuật: Module Retrieval Pipeline (Thành viên 2)

> **Mục tiêu module**: Thiết kế, triển khai, hiệu chỉnh (calibrate) và kiểm thử toàn bộ hệ thống tìm kiếm đa tầng (**Hybrid Retrieval Pipeline**), kết hợp giữa ngữ nghĩa (Semantic Dense) và từ khóa chính xác (BM25 Lexical), đồng thời cung cấp cơ chế Fallback thông minh đảm bảo tuân thủ nghiêm ngặt các quy chuẩn giao tiếp (`docs/MODULE_CONTRACTS.md`).

### 1. Các module kỹ thuật thành phần

#### 1.1. Embedding & ChromaDB Indexing (`src/task4_chunking_indexing.py` - phần Indexing)
- **Model Embedding**: Lựa chọn mô hình đa ngôn ngữ hàng đầu **`BAAI/bge-m3`** (vector dimension: 1024), có khả năng nắm bắt ngữ nghĩa tiếng Việt vượt trội trong các tài liệu chính sách và giáo dục.
- **Vector Database**: Cấu hình **ChromaDB** với chế độ `PersistentClient` tại đường dẫn `chroma_db/`.
- **Collection**: Tạo và quản lý collection `rag_documents` với metric khoảng cách Cosine (`hnsw:space: "cosine"`).
- **Lưu trữ Metadata**: Đảm bảo mỗi chunk lưu vào ChromaDB đều lưu kèm các trường metadata bắt buộc: `source`, `title`, `doc_type`, `chunk_index`, `url`.

#### 1.2. Dense / Semantic Search (`src/task5_semantic_search.py`)
- Sử dụng chính hàm `embed_texts()` dùng chung để vectorize query đầu vào.
- Truy vấn $k$ vector gần nhất từ ChromaDB theo cosine distance.
- Chuyển đổi từ Cosine Distance sang Cosine Similarity score chuẩn:
  $$\text{Score}_{\text{cosine}} = \max(0.0, 1.0 - \text{distance})$$
- Sắp xếp danh sách kết quả giảm dần theo score, cắt ngưỡng $top\_k$.
- Đính kèm thuộc tính nhận diện: `retrieval_method = "dense"`.

#### 1.3. Lexical / BM25 Search (`src/task6_lexical_search.py`)
- Xây dựng chỉ mục tìm kiếm từ khóa chính xác bằng thuật toán **BM25Okapi** trên cùng tập chunk chuẩn hóa.
- Tách từ (tokenization) và làm sạch text tiếng Việt nhằm tối ưu hóa việc truy vấn các từ khóa đặc thù (mã ngành, tổ hợp môn, tên quy chế, điểm chuẩn).
- Xuất dữ liệu tuân thủ schema `SearchResult`, sắp xếp giảm dần theo điểm BM25.
- Đính kèm thuộc tính nhận diện: `retrieval_method = "bm25"`.

#### 1.4. Hybrid Fusion với Reciprocal Rank Fusion - RRF (`src/task7_reranking.py`)
- Giải quyết sự bất tương xứng về thang điểm thô giữa Dense (0.0 - 1.0) và BM25 (0 - hàng chục) bằng thuật toán Reciprocal Rank Fusion (RRF).
- Áp dụng công thức tính điểm kết hợp:
  $$RRF(d) = \sum_{m \in \{\text{dense}, \text{bm25}\}} \frac{1}{k + \text{rank}_m(d)}$$
  *(Với $k = 60$ là hằng số làm mượt chuẩn công nghiệp, $\text{rank}_m(d) \ge 1$ là vị trí xếp hạng của tài liệu $d$ trong phương pháp $m$)*.
- Khử trùng lặp (deduplication) dựa trên trường `id` của chunk.
- Sắp xếp kết quả theo điểm RRF giảm dần, lấy đúng $top\_k$, gán nhãn `retrieval_method = "hybrid"`.

#### 1.5. Điều phối Retrieval Pipeline & Cơ chế Fallback (`src/task9_retrieval_pipeline.py`)
- **Điều phối**: Thực thi song song hoặc tuần tự cả hai phương thức tìm kiếm Dense và BM25.
- **Calibrate Threshold**:
  - Thực hiện đo kiểm thực nghiệm trên các tập truy vấn:
    - *Query in-domain* (đúng ngữ cảnh HUST: điểm chuẩn, học phí, phương thức xét tuyển): Điểm Dense Cosine thường đạt $\ge 0.55 - 0.85$.
    - *Query out-of-domain* (ngoài phạm vi hoặc mang tính tổng quát trừu tượng): Điểm Dense Cosine thường $< 0.35$.
  - Thiết lập ngưỡng kích hoạt fallback: **`SCORE_THRESHOLD = 0.35 - 0.40`**.
- **Quy tắc kích hoạt Fallback**:
  - Dựa trên điểm Cosine Similarity gốc cao nhất của Dense Search: `best_dense_score`.
  - Nếu `best_dense_score < score_threshold`: Lập tức fallback sang `pageindex_search()` (`retrieval_method = "pageindex"`) để tìm theo cấu trúc tài liệu tổng thể.
  - Nếu `best_dense_score >= score_threshold`: Giữ nguyên kết quả RRF hybrid.
- **Nguyên tắc Invariant**: Cam kết **RRF chỉ được thực thi duy nhất 1 lần** trong toàn bộ pipeline.

---

### 2. Tiêu chuẩn Hợp đồng dữ liệu (`SearchResult` Contract)

Tất cả các hàm tìm kiếm trong module Retrieval đều bảo đảm trả về danh sách các đối tượng tuân thủ 100% schema `SearchResult`:

```python
{
    "id": str,               # Định danh chunk ổn định, duy nhất (vd: "hust-quy-che-tuyen-sinh-2024-5")
    "content": str,          # Nội dung văn bản của chunk (không rỗng, đúng độ dài)
    "score": float,          # Điểm đánh giá (Cosine similarity, BM25 score, hoặc RRF score)
    "metadata": {            # Metadata nguồn
        "source": str,       # Tên file gốc (vd: "hust-quy-che-tuyen-sinh-2024.md")
        "title": str,        # Tiêu đề tài liệu
        "doc_type": str,     # "legal" hoặc "news"
        "chunk_index": int,  # Thứ tự chunk trong tài liệu (>= 0)
        "url": str | None    # Link gốc (nếu là bài báo/tin tức cào từ web)
    },
    "retrieval_method": str  # "dense" | "bm25" | "hybrid" | "pageindex"
}
```

**Các ràng buộc cốt lõi đã được kiểm chứng:**
1. **Sorted**: Mọi danh sách kết quả đều được sắp xếp theo `score` giảm dần.
2. **Unique**: Không có bất kỳ chunk ID nào bị lặp lại trong cùng một danh sách kết quả trả về.
3. **Bounded**: Độ dài danh sách kết quả luôn $\le top\_k$.
4. **Valid Method**: Giá trị `retrieval_method` luôn phản ánh chính xác nguồn gốc thuật toán xử lý.

---

### 3. Hướng dẫn chạy và Kiểm thử Module Retrieval (TV2)

#### Chạy kiểm tra độc lập từng thành phần:
```bash
# 1. Chạy embedding và nạp dữ liệu vào ChromaDB
python -m src.task4_chunking_indexing

# 2. Kiểm tra module Semantic Dense Search
python -m src.task5_semantic_search

# 3. Kiểm tra module Lexical BM25 Search
python -m src.task6_lexical_search

# 4. Kiểm tra thuật toán RRF Reranking
python -m src.task7_reranking

# 5. Kiểm tra toàn bộ Retrieval Pipeline & Fallback
python -m src.task9_retrieval_pipeline
```

#### Chạy kiểm thử tự động (Unit Test / Contract Test):
```bash
# Chạy các test case riêng cho module Retrieval
pytest tests/test_contracts.py -k "semantic or lexical or rrf or retrieve" -v

# Chạy toàn bộ suite test contract
pytest tests/test_contracts.py -q
```

---

### 4. Bảng kiểm tra tiến độ Module Retrieval (TV2 Checklist)

- [x] Khởi tạo và kết nối ChromaDB với Cosine Distance space (`hnsw:space: "cosine"`).
- [x] Cài đặt hàm trích xuất Dense Search với embedding đồng bộ `BAAI/bge-m3`.
- [x] Cài đặt BM25 Lexical Search trên cùng tập chunk corpus chuẩn hóa.
- [x] Lập trình thuật toán Reciprocal Rank Fusion ($k=60$) khử trùng ID và hợp nhất thứ tự.
- [x] Xây dựng cơ chế Fallback linh hoạt dựa trên Dense Cosine score gốc và ngưỡng Calibrated.
- [x] Đảm bảo cấu trúc dữ liệu `SearchResult` thỏa mãn 100% các validation invariants.
- [x] Bàn giao giao diện lập trình ổn định `retrieve(query, top_k, score_threshold, use_reranking)` cho TV3 (Generation).

---

## 🚀 Quick start chung cho toàn bộ dự án

```bash
# Tạo môi trường ảo và cài đặt thư viện
python -m venv .venv
source .venv/bin/activate       # Trên Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
python -m playwright install chromium
cp .env.example .env
```

Điền các API key cần thiết vào `.env` (Gemini, OpenAI, Cohere nếu có). Không commit file `.env`.

```bash
# 1. Thu thập và chuẩn hoá dữ liệu (TV1)
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown

# 2. Chunking, Indexing và kiểm tra Retrieval (TV1 + TV2)
python -m src.task4_chunking_indexing
pytest tests/test_contracts.py -q

# 3. Chạy ứng dụng Chatbot Streamlit (TV4)
streamlit run app.py
```

---

## ⏱️ Lộ trình triển khai 3 giờ

| Mốc | Thời gian | Kết quả cần đạt | Thành viên phụ trách |
| :--- | :---: | :--- | :---: |
| **0. Setup** | 10 phút | Môi trường và `.env` sẵn sàng | Cả nhóm |
| **1. Data** | 25 phút | ≥3 legal, ≥5 news, Markdown đã chuẩn hoá | **TV1** |
| **2. Index & Search** | 30 phút | ChromaDB, Dense search và BM25 chạy được | **TV2** |
| **3. Fusion & Fallback** | 25 phút | RRF và Fallback tuân thủ contract, calibrate threshold | **TV2** |
| **4. Generation & UI** | 30 phút | Chatbot trả lời có citation, safe refusal | **TV3** |
| **5. Evaluation** | 30 phút | 15+ Q&A, 4 metric, A/B comparison (`RESULT.md`) | **TV4** |
| **6. Demo & Handoff** | 30 phút | Test toàn bộ hệ thống, báo cáo cá nhân và push repo | Cả nhóm |

---

## 📌 Quy tắc chất lượng mã nguồn (Code Quality Rules)

- **Đồng nhất Schema**: Dense Search và BM25 Search bắt buộc cùng trả về `SearchResult` theo một schema chuẩn duy nhất.
- **RRF duy nhất**: RRF chỉ dùng để gộp thứ hạng và chỉ được chạy một lần duy nhất trong toàn pipeline.
- **Ngưỡng Fallback**: Quyết định fallback bắt buộc dùng điểm Cosine gốc của Dense Retrieval, không dùng điểm RRF.
- **Hiệu chỉnh Threshold**: Ngưỡng phải được hiệu chỉnh trên query in-domain và out-of-domain, không áp dụng một con số cứng nhắc mà không có cơ sở dữ liệu.
- **Bảo toàn ID**: Quá trình reorder chunk cho LLM (TV3) không được làm mất hoặc sai lệch ID gốc của chunk.

---

## 📂 Danh mục tài liệu dự án

- [Module contracts](docs/MODULE_CONTRACTS.md): Quy định chi tiết về schema, interface và các invariant của hệ thống.
- [Step-by-step guide](docs/STEP_BY_STEP.md): Hướng dẫn từng bước triển khai và tiêu chí nghiệm thu.
- [Grading rubric](docs/GRADING_RUBRIC.md): Thang điểm đánh giá của giảng viên/mentor.
- [Individual report template](reports/INDIVIDUAL_REPORT.md): Mẫu báo cáo đóng góp cá nhân của từng thành viên.
- [Evaluation Results](reports/RESULT.md): Báo cáo kết quả đánh giá 4 metrics và A/B testing.

---

## 🧪 Lệnh chạy kiểm thử (Tests)

```bash
# 1. Kiểm tra Contract tests (giao diện, schema và kiểu dữ liệu)
pytest tests/test_contracts.py -v

# 2. Kiểm tra Acceptance tests (kiểm tra tính năng toàn diện end-to-end)
pytest tests/test_acceptance.py -v

# 3. Chạy toàn bộ test suite
pytest -q
```
