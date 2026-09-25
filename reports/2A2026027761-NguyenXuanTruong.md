# Individual contribution report

## Thông tin

* Họ và tên: Nguyễn Xuân Trường
* Mã học viên: 2A202602761
* Nhóm: FourBro
* Repository/branch: `D:\BaiLab\lab8s\K4-Day08-FourBro` / branch: TODO

## Phần việc đã thực hiện

| Module/deliverable                    | Việc tôi trực tiếp làm                                                                                                               | File/commit/PR                                                                                                                                | Trạng thái |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Streamlit chatbot                     | Hoàn thiện giao diện chatbot, khu vực hiển thị câu trả lời và thông tin liên quan đến retrieval/evaluation theo yêu cầu của Module 4 | `app.py`                                                                                                                                      | Done       |
| Golden Q&A dataset                    | Tạo Golden Dataset gồm 18 câu hỏi, bao phủ các nhóm câu hỏi của đề tài tuyển sinh đại học và có câu hỏi adversarial                  | `group_project/evaluation/golden_dataset.json`                                                                                                | Partial    |
| Evaluation report                     | Tạo file kết quả evaluation theo đúng cấu trúc yêu cầu, chuẩn bị các mục cho 4 metric và A/B comparison                              | `group_project/evaluation/RESULT.md`                                                                                                          | Partial    |
| Evaluation preparation                | Kiểm tra khả năng chạy retrieval pipeline và generation pipeline để chuẩn bị cho evaluation                                          | `src/task5_semantic_search.py`, `src/task6_bm25_search.py`, `src/task7_rrf.py`, `src/task9_retrieval_pipeline.py`, `src/task10_generation.py` | Partial    |
| Retrieval/evaluation integration test | Chạy thử pipeline và xác định các lỗi ngăn evaluation chạy end-to-end                                                                | Terminal test output                                                                                                                          | Done       |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng Golden Dataset riêng cho evaluation với 18 câu hỏi thay vì đánh giá bằng các câu hỏi nhập ngẫu nhiên.

   **Lý do/evidence:** Golden Dataset được tạo tại `group_project/evaluation/golden_dataset.json`, gồm 18 câu hỏi và được tổ chức theo format phục vụ evaluation. Dataset có nhiều nhóm câu hỏi và có câu hỏi adversarial để kiểm tra trường hợp hệ thống không đủ bằng chứng.

   **Trade-off:** Việc xây dựng Golden Dataset mất thời gian chuẩn bị và cần bổ sung `expected_answer`/`expected_context` chính xác trước khi chạy metric. Đổi lại, kết quả evaluation có cùng một tập câu hỏi để so sánh giữa các cấu hình retrieval.

2. **Quyết định:** Tách riêng kết quả evaluation thành `RESULT.md` thay vì ghi trực tiếp kết quả vào source code.

   **Lý do/evidence:** File `group_project/evaluation/RESULT.md` được tạo theo cấu trúc yêu cầu, gồm Run information, Configurations, Overall scores, A/B comparison, Worst performers, Recommendations và Bonus experiments.

   **Trade-off:** Báo cáo phụ thuộc vào kết quả chạy thực tế của backend và Golden Dataset hoàn chỉnh. Khi các thành phần retrieval/generation chưa chạy end-to-end thì không thể điền số liệu giả vào báo cáo.

## Kiểm thử và kết quả

* Test hoặc query tôi đã dùng:

  * `python -m src.task9_retrieval_pipeline`
  * `python -m src.task10_generation`
  * Kiểm tra Task 4–7 và retrieval pipeline.
  * Kiểm tra Golden Dataset gồm 18 câu hỏi.
  * Kiểm tra việc cài đặt `rank-bm25`.

* Kết quả trước/sau nếu có:

  * `rank-bm25` đã được cài đặt thành công, phiên bản `0.2.2`.
  * Task 4 đọc được 8 documents và tạo được 1,135 chunks; validation dữ liệu/chunk thực hiện thành công.
  * Embedding chưa hoàn thành do môi trường thiếu `OPENAI_API_KEY`, vì vậy Chroma chưa có dữ liệu embedding để thực hiện dense retrieval thực tế.
  * Task 5 và Task 6 khi kiểm tra trong trạng thái đó lần lượt không có kết quả dense/BM25 thực tế.
  * Task 7 RRF đã được kiểm tra bằng dữ liệu demo.

* Lỗi đã phát hiện và cách xử lý:

  * `task9_retrieval_pipeline` và `task10_generation` từng dừng tại `src/task5_semantic_search.py` với `NotImplementedError("Implement semantic_search")`.
  * Đã xác định đây là lỗi do semantic search chưa được triển khai đầy đủ.
  * Đã kiểm tra và triển khai/kiểm thử các phần Task 5–7 trong phạm vi cần thiết cho integration.
  * Lỗi thiếu `OPENAI_API_KEY` trong bước embedding được xác định là nguyên nhân khiến Chroma chưa có dữ liệu để evaluation end-to-end.

## Điều còn hạn chế

* Một hạn chế cụ thể của phần tôi làm:

  * Evaluation chưa thể hoàn thành đầy đủ khi retrieval và generation backend chưa chạy end-to-end với dữ liệu embedding thực tế. Vì vậy các giá trị Faithfulness, Answer Relevance, Context Recall và Context Precision chưa có cơ sở để điền.

* Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện:

  * Hoàn thiện `expected_answer` và `expected_context` cho toàn bộ Golden Dataset, sau đó chạy evaluation trên cùng một dataset với Config A và Config B để lấy số liệu thực tế.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

* Ngày: 25/09/2026
* Tên thành viên: Nguyễn Xuân Trường
