# 01. Tổng quan Dự án (Project Overview)

**Loại dự án:** Hybrid Batch Analytics & Near Real-time Transaction Monitoring  
**Trọng tâm chính:** Data Analysis, Data Engineering, Database Design & Visualization  
**Bộ dữ liệu MVP:** Sparkov Credit Card Fraud Detection (`fraudTrain.csv` & `fraudTest.csv`)  
**Trạng thái:** Đã chốt bộ dữ liệu & kiến trúc nền tảng (Đang triển khai)

---

## 1.1. Tầm nhìn (Vision)

Xây dựng một nền tảng dữ liệu hoàn chỉnh có khả năng thu thập (ingest) dữ liệu giao dịch thẻ tín dụng, khám phá và kiểm định chất lượng dữ liệu, chuẩn hóa và lưu trữ trong cơ sở dữ liệu có cấu trúc phân tầng, phát hiện các hành vi giao dịch đáng ngờ, và trình bày các góc nhìn phân tích chuyên sâu thông qua hệ thống Dashboard tương tác.

Nền tảng hỗ trợ song song hai chế độ vận hành:

- **Batch Analytics (Phân tích theo lô):** Xử lý, làm sạch và phân tích chuyên sâu lịch sử giao dịch quy mô lớn (~1.85 triệu bản ghi từ bộ dữ liệu Sparkov).
- **Near Real-time Monitoring (Giám sát cận thời gian thực):** Giả lập luồng giao dịch phát sinh liên tục qua Kafka và cập nhật tức thời các bảng giám sát, cảnh báo gian lận khi sự kiện mới được xử lý.

> **Định hướng cốt lõi:** Dự án đặt trọng tâm vào **vòng đời dữ liệu toàn diện (End-to-End Data Lifecycle)** — từ thu thập, kiểm định, thiết kế kho dữ liệu, tạo đặc trưng đến trực quan hóa và giám sát vận hành — thay vì chỉ chạy đua độ phức tạp của các thuật toán học sâu (Deep Learning).

---

## 1.2. Mục tiêu Cụ thể (Objectives)

1. **Thu thập dữ liệu (Ingestion):** Nạp dữ liệu lịch sử từ file CSV/Parquet và dữ liệu giao dịch giả lập theo thời gian thực.
2. **Phân tích khám phá (EDA):** Khám phá phân phối giao dịch, quy luật thời gian, vị trí địa lý, hành vi chi tiêu theo thẻ và hiện tượng mất cân bằng nhãn.
3. **Xây dựng Pipeline tiền xử lý tái lập được (Repeatable ETL/ELT):** Làm sạch, chuẩn hóa tên cột, ép kiểu tối ưu bộ nhớ và biến đổi dữ liệu tự động.
4. **Kiểm định chất lượng & Truy vết nguồn gốc (Data Quality & Lineage):** Xác thực schema bằng Pandera, ghi nhận các bản ghi lỗi và theo dõi mã lô nạp (`batch_id`).
5. **Thiết kế Cơ sở dữ liệu PostgreSQL đa tầng:** Phục vụ đồng thời tác vụ vận hành (OLTP / Core) và tác vụ truy vấn phân tích, báo cáo (OLAP / Star Schema).
6. **Kỹ thuật Đặc trưng (Feature Engineering):** Trích xuất các đặc trưng hành vi theo thẻ tín dụng (`cc_num` velocity windows `1h`, `6h`, `24h`), khoảng cách địa lý Haversine, vận tốc di chuyển ngầm định (`implied_speed_kmh`) và tương tác danh mục chi tiêu.
7. **Phát hiện Giao dịch Đáng ngờ (Fraud Detection):** Kết hợp tập luật nghiệp vụ có khả năng giải thích rõ ràng (Explainable Rules) và mô hình Machine Learning Baseline.
8. **Xây dựng Hệ thống Dashboard 6 chuyên trang:** Phục vụ phân tích lịch sử, giám sát trực tiếp (Live Monitoring), điều tra chi tiết từng giao dịch (Investigation) và giám sát sức khỏe đường ống dữ liệu (Pipeline Observability).
9. **Đóng gói và Triển khai:** Đóng gói toàn bộ các dịch vụ (PostgreSQL, Kafka, FastAPI, React Dashboard, Pipelines) bằng **Docker Compose**.

---

## 1.3. Đối tượng Người dùng Mục tiêu (Intended Users)

| Nhóm người dùng | Nhu cầu sử dụng chính | Trang Dashboard / Công cụ trọng tâm |
| :--- | :--- | :--- |
| **Data Analyst** | Khám phá xu hướng chi tiêu, phân phối số tiền, hành vi chủ thẻ theo khung giờ, độ tuổi, vùng địa lý và danh mục cửa hàng (`category`). | *Transaction Analytics*, *Fraud Analytics*, Notebooks EDA |
| **Fraud Analyst** | Rà soát các giao dịch bị gắn cờ nghi ngờ, kiểm tra lý do cảnh báo (luật nào kích hoạt, chỉ số nào bất thường) và xác minh/cập nhật trạng thái điều tra. | *Live Monitoring*, *Transaction Investigation* |
| **Data Engineer** | Giám sát quá trình nạp dữ liệu, tỷ lệ bản ghi hợp lệ/lỗi, độ trễ xử lý của pipeline và độ trễ tiêu thụ (Consumer Lag) trên Kafka. | *Data Quality & Pipeline Monitoring* |
| **Manager / Executive** | Nắm bắt nhanh các chỉ số KPI tổng quan về lưu lượng giao dịch, tổng giá trị nghi ngờ gian lận và xu hướng tỷ lệ gian lận theo thời gian. | *Executive Overview* |

---

## 1.4. Phạm vi Dự án (Scope)

### Trong phạm vi (In Scope)

- Thu thập dữ liệu lịch sử từ bộ dữ liệu **Sparkov Credit Card Fraud** (`fraudTrain.csv`, `fraudTest.csv`).
- Bộ giả lập sự kiện giao dịch thẻ tín dụng (Transaction Simulator).
- Đường ống xử lý dữ liệu theo lô (Batch ETL/ELT) và lưu trữ trung gian bằng Parquet.
- Hồ sơ hóa dữ liệu (Data Profiling) và kiểm định chất lượng tự động (Pandera).
- Lưu trữ PostgreSQL với 3 schema: `raw`, `core`, `analytics`.
- Trích xuất đặc trưng chuỗi thời gian, không gian địa lý và nhân khẩu học.
- Phát hiện gian lận bằng hệ thống luật (Rule-based Engine) và mô hình ML Baseline.
- Mô hình hóa dữ liệu phân tích (Star Schema & Analytical Views).
- Hệ thống Backend REST API + SSE/WebSocket (FastAPI) và Frontend Dashboard (React + TypeScript).
- Mở rộng luồng xử lý sự kiện thời gian thực với Apache Kafka.
- Giám sát vận hành pipeline và đóng gói Docker Compose.

### Ngoài phạm vi (Out of Scope)

- Kết nối trực tiếp vào hệ thống Core Banking hoặc cổng thanh toán thật (Visa/Mastercard/NAPAS).
- Thực hiện lệnh chuyển tiền thật hoặc tự động chặn/khóa thẻ tín dụng ngoài đời thực.
- Hệ thống ra quyết định chặn giao dịch độ trễ cực thấp cấp độ Production ngân hàng (< 10ms SLA).
- Nghiên cứu các kiến trúc Deep Learning / Graph Neural Networks quá phức tạp vượt ngoài mục tiêu nền tảng dữ liệu.

> *Lưu ý:* Đây là nguyên mẫu hệ thống phục vụ mục đích kỹ thuật dữ liệu, phân tích và nghiên cứu ứng dụng, không phải hệ thống ra quyết định tài chính thương mại trực tiếp.

---

## 1.5. Câu chuyện Xuyên suốt của Dữ liệu (Final Product Narrative)

Sản phẩm hoàn chỉnh minh họa trọn vẹn một hành trình dữ liệu (End-to-End Data Journey) qua 10 bước:

1. **Dữ liệu đi vào nền tảng:** Một lô dữ liệu lịch sử Sparkov CSV hoặc một luồng sự kiện giao dịch thẻ tín dụng giả lập được đẩy vào hệ thống.
2. **Ghi nhận nguyên trạng:** Tầng Ingestion lưu lại bản ghi gốc (`raw_transactions`) kèm thông tin định danh lô nạp (`ingestion_batches`).
3. **Kiểm định chất lượng:** Tầng Validation phát hiện các bản ghi thiếu trường bắt buộc, sai kiểu dữ liệu, giá trị âm/ngoại lai vô lý hoặc trùng lặp mã giao dịch `trans_num`.
4. **Chuẩn hóa & Làm giàu:** Tầng Processing đổi tên các cột nhạy cảm SQL (`state_code`, `lon`, `merch_lon`), chuẩn hóa thời gian và trích xuất đặc trưng hành vi (`1h/6h/24h velocity`, `implied_speed_kmh`).
5. **Lưu trữ đa tầng:** PostgreSQL lưu trữ đồng bộ dữ liệu ở cả 3 tầng `raw`, `core` và `analytics`.
6. **Chấm điểm rủi ro có giải thích:** Bộ máy phát hiện gian lận tính điểm `risk_score`, phân loại mức độ rủi ro (`LOW`, `MEDIUM`, `HIGH`) và lưu kèm lý do giải thích cụ thể vào bảng cảnh báo.
7. **Tổng hợp chỉ số phân tích:** Tầng Analytics cập nhật các bảng Fact, Dimension và các bảng tổng hợp theo giờ/ngày/danh mục với định nghĩa nhất quán giữa Batch và Streaming.
8. **Hiển thị trực quan:** React Dashboard cập nhật biểu đồ xu hướng lịch sử và bảng theo dõi giao dịch thời gian thực.
9. **Điều tra chuyên sâu:** Chuyên viên phân tích gian lận (Fraud Analyst) bấm vào một cảnh báo để xem chi tiết giao dịch, lịch sử quẹt thẻ gần nhất và xác nhận trạng thái (`CONFIRMED_FRAUD` hoặc `FALSE_POSITIVE`).
10. **Giám sát vận hành:** Kỹ sư dữ liệu (Data Engineer) theo dõi lịch sử chạy pipeline, tỷ lệ lỗi dữ liệu và độ trễ hệ thống ngay trên giao diện quản trị.
