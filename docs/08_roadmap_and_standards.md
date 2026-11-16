# 08. Lộ trình Triển khai & Tiêu chuẩn Kỹ thuật (Roadmap, DoD & Engineering Standards)

Tài liệu này quy định lộ trình thực hiện dự án trong 10 tuần, tiêu chí hoàn thành (Definition of Done) cho từng giai đoạn, 10 tiêu chuẩn chất lượng kỹ thuật, tỷ lệ phân bổ nguồn lực và danh sách công việc khởi động (Sprint 0).

---

## 8.1. Lộ trình Triển khai 10 Tuần (Ten-Week Implementation Roadmap)

| Tuần | Trọng tâm triển khai (Focus Area) | Sản phẩm bàn giao (Deliverables) | Trạng thái |
| :---: | :--- | :--- | :---: |
| **1** | **Khám phá dữ liệu & EDA trên Sparkov** | Notebook `01_eda.ipynb`, Từ điển dữ liệu (`03_data_dictionary.md`), Báo cáo phát hiện EDA (`05_pipelines_and_eda.md`) | Đã hoàn thành |
| **2** | **Làm sạch & Kiểm định chất lượng dữ liệu** | Module `preprocessing/loader.py`, `cleaner.py`, `validation.py` (Pandera) và Parquet trung gian (`data/interim/`) | Đang triển khai |
| **3** | **Kỹ thuật Đặc trưng & Chia tập chống rò rỉ** | Module `preprocessing/splitter.py` (Out-of-Time split) và `feature_engineering.py` (`1h/6h/24h velocity`, `implied_speed_kmh`...) | Kế hoạch |
| **4** | **Thiết kế PostgreSQL 3 tầng & Migrations** | DDL `database/schema.sql`, ORM `models.py`, `repository.py` cho 3 schemas `raw`, `core`, `analytics` | Kế hoạch |
| **5** | **Đường ống Batch ETL/ELT hoàn chỉnh** | Script `scripts/run_preprocessing.py` nạp tự động từ CSV $\rightarrow$ `raw` $\rightarrow$ `core` $\rightarrow$ `transaction_features` (Idempotent) | Kế hoạch |
| **6** | **Mô hình hóa Analytics & SQL Data Marts** | Các bảng Star Schema (`fact_transactions`, `dim_*`) và SQL Views / Materialized Views tổng hợp (`agg_*`) | Kế hoạch |
| **7** | **Phát hiện Gian lận (Rules + ML Baseline)** | Bộ quy tắc `R001–R006`, mô hình ML Baseline, kịch bản huấn luyện/đánh giá (`PR-AUC`, `F1`, `Value Recall`) | Kế hoạch |
| **8** | **FastAPI Backend & React Dashboard MVP** | Các REST API `/api/v1/*` và các trang Dashboard phân tích lịch sử, điều tra giao dịch | Kế hoạch |
| **9** | **Kafka Streaming & Transaction Simulator** | `scripts/simulate_transactions.py`, Kafka Producer/Consumer chấm điểm thời gian thực vào PostgreSQL | Kế hoạch |
| **10** | **Live Monitoring, Kiểm thử & Đóng gói Docker** | Tích hợp SSE/WebSocket cho trang *Live Monitoring*, hoàn thiện Pytest (`tests/`) và `docker-compose.yml` | Kế hoạch |

> **Nguyên tắc Ưu tiên:** Luôn ưu tiên hoàn thiện và kiểm thử kỹ lưỡng **Batch Pipeline + PostgreSQL + API** trước khi mở rộng sang **Kafka Streaming**.

---

## 8.2. Tiêu chí Hoàn thành theo Giai đoạn (Definition of Done — DoD)

### Giai đoạn 1 — Khám phá Dữ liệu (Data Exploration)

- [x] Hiểu rõ và chuẩn hóa toàn bộ 22 trường gốc của bộ dữ liệu **Sparkov Credit Card Fraud**.
- [x] Hoàn thành phân tích giá trị khuyết, bản ghi trùng lặp và phạm vi thời gian (`2019–2020`).
- [x] Định lượng tỷ lệ mất cân bằng nhãn (`0.579%` trên Train, `0.386%` trên Test) và phân phối giữa nhóm gian lận vs hợp lệ.
- [x] Tạo bộ biểu đồ phân tích EDA (`reports/figures/01..08_*.png`) kèm nhận xét định lượng chi tiết.
- [x] Ghi nhận rõ hiện tượng Concept Drift nhẹ và 16 thẻ Cold-Start ở tập Test.

### Giai đoạn 2 — Kỹ thuật Dữ liệu (Data Engineering)

- [ ] Dữ liệu nguồn gốc được lưu trữ nguyên vẹn trong `raw.raw_transactions` kèm `batch_id`.
- [ ] Pipeline làm sạch và chuẩn hóa tên cột (`state_code`, `lon`, `merch_lon`) chạy tự động, ổn định.
- [ ] Kiểm định chất lượng dữ liệu bằng Pandera được cài đặt đầy đủ.
- [ ] Các bản ghi không hợp lệ được đánh dấu và lưu vết lỗi trong `raw`, không bị xóa âm thầm.
- [ ] Chạy lại pipeline nạp dữ liệu nhiều lần không tạo ra giao dịch trùng lặp (`trans_num` idempotency).
- [ ] Schema PostgreSQL 3 tầng và các script migration hoạt động hoàn chỉnh.

### Giai đoạn 3 — Mô hình hóa Phân tích (Analytics Modeling)

- [ ] Mô hình Star Schema (`analytics.fact_transactions`, `dim_time`, `dim_cards`, `dim_merchants`, `dim_categories`) và các view tổng hợp hoạt động chính xác.
- [ ] Các truy vấn tổng hợp SQL được tài liệu hóa và tối ưu bằng Index.
- [ ] Các chỉ số theo thời gian (giờ, ngày, tháng), theo danh mục (`category`) và theo bang (`state_code`) sẵn sàng phục vụ API.
- [ ] Định nghĩa các chỉ số (`Suspicious Rate` vs `Confirmed Fraud Rate`) nhất quán tuyệt đối trên toàn hệ thống.

### Giai đoạn 4 — Phát hiện Gian lận & Giao diện Dashboard (Detection & Dashboard)

- [ ] Hệ thống luật nghiệp vụ (`R001–R006`) và mô hình ML Baseline hoạt động ổn định.
- [ ] Kết quả dự đoán (`fraud_predictions`), cảnh báo (`fraud_alerts`) và nhãn thực tế (`transaction_labels`) được lưu trữ tách biệt.
- [ ] Trang *Executive Overview*, *Transaction Analytics* và *Fraud Analytics* hiển thị đầy đủ KPI và biểu đồ.
- [ ] Trang *Transaction Investigation* cho phép xem chi tiết giải thích cảnh báo, lịch sử thẻ 24h và cập nhật trạng thái điều tra.
- [ ] Trang *Data Quality & Pipeline Monitoring* hiển thị lịch sử các đợt chạy nạp dữ liệu và tỷ lệ lỗi.

### Giai đoạn 5 — Xử lý Thời gian Thực (Kafka Streaming)

- [ ] `scripts/simulate_transactions.py` phát sự kiện giao dịch từ tập Test lên Kafka topic `transactions`.
- [ ] Python Consumer tiêu thụ sự kiện, tính đặc trưng cửa sổ trượt và chấm điểm rủi ro theo thời gian thực.
- [ ] Xử lý an toàn các sự kiện gửi trùng (duplicate delivery) và cô lập các message lỗi định dạng.
- [ ] Giao dịch mới xuất hiện ngay trong PostgreSQL và được đẩy qua SSE/WebSocket lên trang *Live Monitoring*.
- [ ] Hiển thị được độ trễ xử lý (`processing_latency_ms`) và độ trễ hàng đợi (`consumer_lag`).

---

## 8.3. 10 Tiêu chuẩn Chất lượng Kỹ thuật (Engineering Quality Requirements)

Dự án tuân thủ nghiêm ngặt 10 nguyên tắc kỹ thuật dữ liệu:

1. **Data Quality (Chất lượng dữ liệu):** Xác thực tự động schema, kiểu dữ liệu, trường bắt buộc, miền giá trị (`amt > 0`, tọa độ hợp lệ) và tính duy nhất của khóa `trans_num`.
2. **Data Lineage (Truy vết nguồn gốc):** Mọi bản ghi giao dịch đều truy ngược được về nguồn phát sinh (`source_name`) và mã lô nạp (`batch_id`).
3. **Idempotency (Tính lũy đẳng):** Có thể chạy lại bất kỳ bước nạp hoặc xử lý nào mà không làm sai lệch số liệu hay nhân đôi bản ghi.
4. **Temporal Correctness (Tính chính xác thời gian):** Phân biệt rõ ràng 4 mốc thời gian: thời điểm giao dịch xảy ra (`event_time`), thời điểm hệ thống nhận (`ingested_at`), thời điểm dự đoán (`predicted_at`) và thời điểm xác nhận nhãn (`labeled_at`).
5. **Analytical Modeling (Mô hình hóa phân tích):** Thiết kế tầng `analytics` theo Star Schema và đánh chỉ mục hợp lý để các truy vấn Dashboard phản hồi nhanh.
6. **Reproducibility (Khả năng tái lập):** Quản lý phiên bản cho toàn bộ mã nguồn, cấu hình (`configs/config.yaml`), hạt giống ngẫu nhiên (`seed: 42`), schema DB và mô hình.
7. **Observability (Khả năng quan sát):** Ghi log đầy đủ lịch sử chạy pipeline, số lượng bản ghi thành công/thất bại, thời gian thực thi và nguyên nhân lỗi.
8. **Metric Consistency (Tính nhất quán độ đo):** Sử dụng cùng một định nghĩa đặc trưng và chỉ số nghiệp vụ giữa luồng Batch và luồng Streaming.
9. **Leakage Prevention (Chống rò rỉ dữ liệu):** Không bao giờ để lộ nhãn tương lai (`is_fraud`) hoặc các sự kiện xảy ra sau thời điểm giao dịch hiện tại vào quá trình tính đặc trưng và dự đoán trực tuyến.
10. **Explainability (Khả năng giải thích):** Mọi cảnh báo gian lận đều lưu kèm phiên bản mô hình/tập luật và danh sách lý do cụ thể (`alert_reason` JSONB).

---

## 8.4. Phân bổ Nguồn lực Đề xuất (Suggested Effort Allocation)

| Hạng mục công việc | Tỷ trọng thời gian đề xuất | Ghi chú trọng tâm |
| :--- | :---: | :--- |
| **Data Engineering & ETL/Streaming Pipelines** | **30%** | Làm sạch, kiểm định Pandera, tính toán cửa sổ trượt, Batch & Kafka Consumer. |
| **Data Analysis & Exploratory Data Analysis (EDA)** | **25%** | Khám phá quy luật dữ liệu Sparkov, chứng minh giả thuyết đặc trưng và калиб ngưỡng luật. |
| **Database Design & Analytical SQL** | **20%** | Thiết kế PostgreSQL 3 schemas (`raw`, `core`, `analytics`), indexing, views & truy vấn tối ưu. |
| **Dashboard UI & Backend API Visualization** | **15%** | Xây dựng FastAPI endpoints và 6 trang React + TypeScript Dashboard. |
| **Machine Learning & Rule Engine Calibration** | **10%** | Xây dựng tập luật `R001–R006`, mô hình ML Baseline và đánh giá Out-of-Time. |

---

## 8.5. Danh sách Công việc Sprint 0 (Immediate Starting Checklist)

Sprint 0 tập trung hoàn toàn vào việc làm chủ bộ dữ liệu **Sparkov** và chuẩn hóa tài liệu trước khi viết code hạ tầng phức tạp:

### Task 1: Chuẩn bị Bộ dữ liệu (`data/`)
- [x] Tải bộ dữ liệu **Sparkov Credit Card Fraud** (`fraudTrain.csv` và `fraudTest.csv`).
- [x] Đặt file gốc vào thư mục `data/raw/`.
- [x] Xác nhận định dạng CSV, bảng mã UTF-8 và cấu trúc 23 cột gốc.
- [x] Tạo file Parquet đã làm sạch sơ bộ trong `data/interim/` (`train_cleaned.parquet`, `test_cleaned.parquet`).

### Task 2: Hiểu Dữ liệu & Chuẩn hóa Schema (`configs/` & `docs/`)
- [x] Kiểm tra kiểu dữ liệu, giá trị khuyết (`0%`) và tính duy nhất của `trans_num`.
- [x] Chốt quy tắc đổi tên 3 cột trùng từ khóa SQL: `state` $\rightarrow$ `state_code`, `long` $\rightarrow$ `lon`, `merch_long` $\rightarrow$ `merch_lon`.
- [x] Chốt danh sách cột loại bỏ khi huấn luyện: `Unnamed: 0`, `first`, `last`, `street`.

### Task 3: Phân tích Khám phá Dữ liệu (`notebooks/01_eda.ipynb`)
- [x] Phân tích tỷ lệ mất cân bằng nhãn (`is_fraud`).
- [x] Phân tích phân phối số tiền `amt` và tương tác `category × amt`.
- [x] Phân tích quy luật giờ trong ngày (`22h–04h`), thứ trong tuần và xu hướng theo tháng.
- [x] Phân tích chùm gian lận (*Fraud Burst*) trên các cửa sổ trượt `1h`, `6h`, `24h` theo thẻ `cc_num`.
- [x] Kiểm chứng khoảng cách địa lý Haversine và vận tốc di chuyển `implied_speed_kmh` (*Impossible Travel*).
- [x] Kiểm tra Drift và độ phủ thực thể (`cc_num`, `merchant`) giữa tập Train và tập Test.

### Task 4: Tài liệu hóa Kiến trúc & Đặc tả (`docs/`)
- [x] Hoàn thiện bộ 8 tài liệu kỹ thuật trong thư mục `docs/` kèm mục lục `docs/README.md`.
- [ ] Bước tiếp theo (Sprint 1): Hoàn thiện mã nguồn trong `preprocessing/` (`loader.py`, `cleaner.py`, `splitter.py`, `feature_engineering.py`, `pipeline.py`) và unit tests trong `tests/test_preprocessing.py`.
