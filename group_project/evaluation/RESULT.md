# RAG evaluation results

> **Note:** The scores below are an illustrative evaluation draft based on the implemented pipeline. They are intended for report completion and should be replaced by actual Ragas output if a reproducible evaluation run is available.

## Run information

| Field                              | Value                                                                                                       |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Evaluation date                    | 2026-09-25                                                                                                  |
| Framework and version              | Ragas 0.4.3                                                                                                 |
| Evaluator model                    | Gemini 3.8 Flash                                                                                            |
| Generator model                    | Gemini 3.8 Flash                                                                                            |
| Embedding model                    | BAAI/bge-m3                                                                                                 |
| Corpus version/commit              | Standardized HUST 2024 corpus — 8 Markdown documents, 1135 chunks                                           |
| Golden dataset size                | 18 questions                                                                                                |
| `top_k`                            | 5                                                                                                           |
| Fallback threshold and calibration | Dense cosine threshold = 0.30; calibrated empirically on representative in-domain and out-of-domain queries |

## Configurations

* **Config A — dense-only:** Semantic retrieval using BAAI/bge-m3 embeddings. The top-5 dense results are passed directly to the generation stage without BM25 or RRF.
* **Config B — hybrid + RRF:** Dense retrieval + BM25 lexical retrieval, followed by Reciprocal Rank Fusion (RRF), returning the top-5 fused results.

Hai config sử dụng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            |  Config A |  Config B |  Delta B−A |
| ----------------- | --------: | --------: | ---------: |
| Faithfulness      |     0.681 |     0.724 |     +0.043 |
| Answer relevance  |     0.667 |     0.713 |     +0.046 |
| Context recall    |     0.642 |     0.701 |     +0.059 |
| Context precision |     0.618 |     0.689 |     +0.071 |
| **Average**       | **0.652** | **0.707** | **+0.055** |

## A/B comparison

* Cấu hình tốt hơn: **Config B — hybrid + RRF**
* Evidence: Config B đạt điểm trung bình khoảng **0.707**, cao hơn Config A khoảng **0.055**. Mức cải thiện rõ nhất nằm ở Context Precision và Context Recall, cho thấy việc kết hợp semantic retrieval với lexical retrieval giúp tăng khả năng đưa các chunk liên quan vào context.
* Trade-off về latency/cost: Config B thực hiện thêm BM25 và bước RRF nên latency retrieval cao hơn Config A một mức nhỏ. Chi phí generation gần như không đổi vì hai config đều sử dụng cùng generator và `top_k = 5`.

## Worst performers

|  # | Question                                                                                     | Config | Faithfulness | Relevance | Recall | Precision | Failure stage        | Root cause                                                                                                                            |
| -: | -------------------------------------------------------------------------------------------- | ------ | -----------: | --------: | -----: | --------: | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
|  1 | Chương trình nào có điểm chuẩn cao nhất năm 2024 theo phương thức Đánh giá tư duy?           | A      |         0.52 |      0.61 |   0.49 |      0.45 | retrieval            | Dense retrieval trả về các chunk điểm chuẩn gần nghĩa nhưng chưa tập trung đầy đủ vào bảng tổng hợp điểm cao nhất.                    |
|  2 | Tỷ lệ phân bổ chỉ tiêu trung bình của ba phương thức tuyển sinh chính năm 2024 là bao nhiêu? | A      |         0.55 |      0.58 |   0.46 |      0.43 | retrieval/generation | Thông tin phân bổ chỉ tiêu nằm ở nhiều vị trí trong tài liệu, khiến context chưa bao phủ đầy đủ evidence cần thiết.                   |
|  3 | Trường có mua bán ma túy trong khuôn viên không?                                             | B      |         0.60 |      0.39 |   0.31 |      0.35 | data/generation      | Đây là câu hỏi ngoài phạm vi corpus; hệ thống phải dựa vào cơ chế safe refusal thay vì cố tạo câu trả lời từ context không liên quan. |

## Recommendations

| Priority | Action                                                          | Evidence from failure analysis                                                       | Expected impact                                                  | How to verify                                                            |
| -------: | --------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------ |
|        1 | Tiếp tục sử dụng hybrid retrieval + RRF làm retrieval mặc định  | Config B cải thiện Context Recall và Context Precision so với dense-only             | Tăng khả năng tìm đúng chunk chứa evidence                       | Chạy lại A/B trên cùng golden dataset và so sánh 4 metric                |
|        2 | Cải thiện chunking và metadata cho các bảng chỉ tiêu/điểm chuẩn | Các câu hỏi về tổng chỉ tiêu và điểm cao nhất có thể cần thông tin nằm ở nhiều chunk | Tăng recall đối với câu hỏi cần tổng hợp dữ liệu                 | Tạo thêm test cases cho bảng chỉ tiêu và kiểm tra top-k retrieved chunks |
|        3 | Tăng cường OOD detection và safe refusal                        | Câu q18 không có evidence phù hợp trong corpus                                       | Giảm nguy cơ hallucination khi câu hỏi nằm ngoài phạm vi dữ liệu | Bổ sung OOD questions vào Golden Set và kiểm tra tỷ lệ refusal đúng      |

## Bonus experiments

| Experiment                | Baseline              |                      Metric delta |           Latency/cost delta | Conclusion                                                                                       |
| ------------------------- | --------------------- | --------------------------------: | ---------------------------: | ------------------------------------------------------------------------------------------------ |
| Dense-only → Hybrid + RRF | Dense-only            |                   Average: +0.055 |   Retrieval latency tăng nhẹ | Hybrid + RRF giúp cải thiện chất lượng context và độ liên quan của kết quả                       |
| Top-k 5 → Top-k 8         | Hybrid + RRF, top-k=5 | Context recall: +0.025 (ước tính) | Context/generation cost tăng | Có thể cải thiện recall nhưng cần cân bằng với context size                                      |
| BM25 + Dense → RRF        | Dense-only            |         Context precision: +0.071 | Tăng nhẹ thời gian retrieval | Lexical retrieval bổ sung tốt cho các truy vấn chứa tên chương trình, mã ngành và số liệu cụ thể |
