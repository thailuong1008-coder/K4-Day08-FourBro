# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Mạnh Tiến
- Mã học viên: 2A202602506
- Nhóm: FourBro
- Repository/branch: `https://github.com/thailuong1008-coder/K4-Day08-FourBro` / `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 8 — PageIndex fallback | Viết `upload_documents()` (upload PDF pháp lý qua PageIndex SDK, cache doc_id) và `pageindex_search()` (query + parse kết quả thành SearchResult) | `src/task8_pageindex_vectorless.py` | Done |
| Task 9 — Retrieval pipeline | Viết `retrieve()`: gộp dense + BM25 qua RRF một lần, quyết định fallback dựa trên cosine score gốc của dense (không dùng RRF score), bắt lỗi khi PageIndex fail | `src/task9_retrieval_pipeline.py` | Done |
| Task 10 — Generation có citation | Viết `reorder_for_llm`, `format_context`, `call_llm` (dispatch OpenAI/Anthropic/Gemini theo `.env`), `generate_with_citation` với safe refusal khi thiếu evidence hoặc LLM lỗi | `src/task10_generation.py` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Dùng cosine score gốc của dense search (không dùng RRF score) để quyết định fallback sang PageIndex.  
   **Lý do/evidence:** RRF score chỉ phản ánh thứ hạng tương đối, không có ý nghĩa tuyệt đối để so với threshold; contract test `test_retrieve_uses_dense_score_for_fallback` xác nhận yêu cầu này.  
   **Trade-off:** Nếu dense search yếu (embedding kém) thì threshold dễ bị kích hoạt sai, phải calibrate kỹ với query in-domain/out-of-domain.

2. **Quyết định:** Khi PageIndex lỗi hoặc LLM provider lỗi, hệ thống trả kết quả hybrid/safe refusal thay vì crash hoặc bịa câu trả lời.  
   **Lý do/evidence:** Yêu cầu bắt buộc trong `MODULE_CONTRACTS.md` ("PageIndex/provider lỗi không được làm UI crash"); test `test_retrieve_survives_fallback_provider_error` xác nhận.  
   **Trade-off:** Người dùng có thể nhận câu trả lời từ chối dù dữ liệu thật ra có tồn tại, nếu provider chỉ lỗi tạm thời.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_contracts.py -q -k "reorder or retrieve or refusal or signatures"` (6/6 pass); chạy thử `python -m src.task10_generation` với 1 câu hỏi trong domain và 1 câu ngoài domain.
- Kết quả trước/sau nếu có: trước khi implement, 3 hàm raise `NotImplementedError`; sau khi implement, đủ contract và pass toàn bộ test liên quan tới Task 8/9/10.
- Lỗi đã phát hiện và cách xử lý: Xử lý ngoại lệ an toàn khi PageIndex API hoặc LLM provider gặp sự cố mạng/timeout bằng khối `try...except`, bảo đảm hệ thống không bị crash.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: `pageindex_search` giả định field response là `results`/`nodes`, cần kiểm tra với response thật từ API khi có key.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: viết thêm test riêng (không phải contract test) mock response thật của PageIndex SDK để chốt đúng tên field.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Nguyễn Mạnh Tiến
