# 05. Thiết kế Pipeline Dữ liệu & Báo cáo Phân tích Khám phá (Pipelines & EDA Insights)

Tài liệu này mô tả chi tiết luồng xử lý dữ liệu theo lô (Batch Pipeline), luồng xử lý thời gian thực (Streaming Pipeline), quy tắc kiểm định chất lượng dữ liệu và các phát hiện thực nghiệm quan trọng từ bước EDA trên bộ dữ liệu **Sparkov Credit Card Fraud**.

---

## 5.1. Thiết kế Đường ống Xử lý Theo lô (Batch ETL/ELT Pipeline)

```text
Sparkov CSV (fraudTrain.csv / fraudTest.csv)
    |
    v
[1. Extract] (preprocessing/loader.py)
    |
    v
[2. Raw Ingestion] --> PostgreSQL: raw.ingestion_batches & raw.raw_transactions
    |
    v
[3. Schema & Data Quality Validation] (Pandera)
    |---> Bản ghi lỗi (Invalid) --> Ghi nhận vào raw_transactions (is_valid=FALSE) & error_summary
    |
    v (Bản ghi hợp lệ)
[4. Cleaning & Standardization] (preprocessing/cleaner.py)
    |   - Đổi tên: state -> state_code, long -> lon, merch_long -> merch_lon
    |   - Loại bỏ: Unnamed: 0, first, last, street
    |   - Chuẩn hóa: trans_date_trans_time, dob; xuất Parquet trung gian (data/interim/)
    v
[5. Core Loading] --> PostgreSQL: core.cards, core.merchants, core.transactions, core.transaction_labels
    |
    v
[6. Feature Engineering] (preprocessing/feature_engineering.py)
    |   - Cửa sổ trượt 1h/6h/24h theo cc_num, Haversine distance, implied_speed_kmh, ratios
    |   --> Lưu vào core.transaction_features & data/processed/
    +-------------------------------+
    |                               |
    v                               v
[7. Fraud Detection]        [8. Analytics Transformations]
(Rules + ML Baseline)       (SQL Star Schema & Aggregations)
    |                               |
    v                               v
core.fraud_predictions &    analytics.fact_transactions,
core.fraud_alerts           dim_*, agg_*
    |                               |
    +---------------+---------------+
                    |
                    v
         [9. Publish via FastAPI]
                    |
                    v
            React Dashboard
```

### Quy tắc Xử lý Bản ghi Lỗi (Quarantine & Observability)

- **Tuyệt đối không âm thầm xóa bỏ các bản ghi lỗi (No Silent Drops):** Mọi bản ghi không vượt qua bước kiểm định Pandera (ví dụ: thiếu `trans_num`, `amt <= 0`, tọa độ vĩ độ nằm ngoài `[-90, 90]`, hoặc trùng lặp `trans_num` trong cùng một lô) đều được đánh dấu `is_valid = FALSE` kèm lý do chi tiết trong `raw.raw_transactions.validation_errors` và tổng hợp lên `raw.ingestion_batches.error_summary`.
- Nhờ cơ chế này, trang **Data Quality & Pipeline Monitoring** trên Dashboard có thể báo cáo chính xác tỷ lệ bản ghi hợp lệ, bản ghi lỗi và nguyên nhân lỗi của từng batch.

---

## 5.2. Kế hoạch & Kết quả Phân tích Khám phá Dữ liệu (EDA Insights — Sparkov)

Quá trình EDA trong `notebooks/01_eda.ipynb` được tổ chức thành **6 mảng phân tích cốt lõi**, cung cấp bằng chứng định lượng trực tiếp để thiết kế Feature Engineering và Rule Engine:

### Bảng Tổng hợp 6 Mảng Phân tích EDA

| Mảng phân tích | Câu hỏi kiểm chứng chính | Kết quả thực nghiệm trên Sparkov (`fraudTrain.csv`) | Quyết định thiết kế suy ra |
| :--- | :--- | :--- | :--- |
| **1. Tổng quan & Chất lượng dữ liệu** | Kích thước, kiểu dữ liệu, tỷ lệ khuyết, tính duy nhất của khóa `trans_num`? | `1,296,675` dòng (Train) và `555,719` dòng (Test); `0%` missing values; `trans_num` duy nhất 100%; tối ưu dtype giúp giảm RAM xuống `~110 MB`. | Sử dụng `trans_num` làm khóa chống trùng lặp (Idempotency key); áp dụng `SPARKOV_DTYPE_MAP` ngay khi đọc file. |
| **2. Phân tích Mất cân bằng Nhãn (Class Imbalance)** | Tỷ lệ gian lận là bao nhiêu? Có chênh lệch giữa Train và Test không? | Train có `7,506` giao dịch gian lận (**`0.579%`**, tỷ lệ `171.8 : 1`). Test có `2,145` giao dịch gian lận (**`0.386%`**). | Không dùng `Accuracy` làm thước đo; bắt buộc dùng **PR-AUC, F1, Recall, Precision** và thiết lập `class_weight` / `scale_pos_weight`. |
| **3. Phân phối Số tiền & Danh mục (`amt` × `category`)** | Số tiền giao dịch gian lận khác biệt thế nào giữa các danh mục chi tiêu? | Trung vị `amt` gian lận toàn cục cao gấp **~8.4 lần** giao dịch hợp lệ. Đặc biệt: ở `shopping_net`, trung vị gian lận là **`$995.57`** (gấp **120 lần** mức hợp lệ `$8.30`); ngược lại ở `gas_transport` và `grocery_net`, kẻ gian lại quẹt thử thẻ ở mức nhỏ **`$10–$12`** (bằng `0.17–0.24` lần mức thường). | Tạo đặc trưng tỷ lệ tương tác **`amt_to_cat_median_ratio`** và **`amt_to_card_mean_ratio`** thay vì chỉ dùng ngưỡng tiền cố định. |
| **4. Quy luật Thời gian (`Temporal Patterns`)** | Gian lận tập trung vào khung giờ nào trong ngày và tháng nào trong năm? | Tỷ lệ gian lận tăng vọt đột biến trong khung giờ đêm khuya **`22:00` – `03:59` sáng** (khi chủ thẻ đang ngủ), cao gấp **5–6 lần** khung giờ ban ngày. | Tạo cờ **`is_night_tx`** (`hour IN {22, 23, 0, 1, 2, 3}`) và biểu đồ Heatmap `Category × Hour of Day` trên Dashboard. |
| **5. Hành vi Chuỗi Giao dịch theo Thẻ (`Fraud Burst & Velocity`)** | Khi một thẻ `cc_num` bị lộ, kẻ gian quẹt bao nhiêu lần và trong bao lâu? | Có `762 / 983` thẻ trên tập Train từng bị gian lận. Một khi thẻ bị lộ, kẻ gian tấn công theo từng "chùm" (**Fraud Burst**) với trung vị **10 giao dịch gian lận liên tiếp / thẻ**. Tổng chi tiêu 24h (`amt_sum_24h`) của nhóm gian lận có trung vị **`$2,242.06`**, gấp **~9.6 lần** nhóm hợp lệ (`$234.08`). | Thiết kế các đặc trưng cửa sổ trượt **`tx_count_1h`, `tx_count_6h`, `tx_count_24h`, `amt_sum_1h`, `amt_sum_24h`** và `time_since_last_tx_sec`. |
| **6. Không gian Địa lý, Vận tốc & Nhân khẩu học** | Khoảng cách địa lý và độ tuổi chủ thẻ ảnh hưởng thế nào đến rủi ro? | Khoảng cách tĩnh từ nhà tới cửa hàng (`dist_home_to_merch_km`) có phân phối tương đương nhau (`~75 km`). Tuy nhiên, **vận tốc di chuyển giữa 2 lần quẹt thẻ liên tiếp (`implied_speed_kmh`)** của nhóm gian lận có trung vị **`64.0 km/h`**, P75 = **`234.0 km/h`**, P90 = **`745.8 km/h`** (*Impossible Travel*). Về độ tuổi, nhóm **`50–65`** và **`65+`** có tỷ lệ gian lận cao nhất (**`0.74%`** vs `0.456%` ở nhóm `35–50`). | Bổ sung **`merch_to_merch_dist_km`**, **`implied_speed_kmh`** và **`customer_age`** vào bộ đặc trưng cốt lõi. |

### Chiến lược Chia tập Dữ liệu Chống Rò rỉ (`preprocessing/splitter.py`)

Từ phân tích Drift & Overlap giữa `fraudTrain.csv` và `fraudTest.csv`:
- Tập Test (`2020-06-21` $\rightarrow$ `2020-12-31`) có **16 thẻ mới tinh (Cold-Start cards)** chưa từng xuất hiện trong tập Train.
- Vì vậy, hệ thống áp dụng chiến lược **Chronological / Out-of-Time Validation Split**:
  1. Sắp xếp toàn bộ `fraudTrain.csv` theo thứ tự tăng dần của `unix_time`.
  2. Lấy `85%` đầu tiên theo thời gian làm **Train Split** và `15%` cuối cùng theo thời gian làm **Validation Split** (tương ứng cấu hình `val_size: 0.15` trong `configs/config.yaml`).
  3. Giữ nguyên `fraudTest.csv` làm **Hold-out Out-of-Time Test Set** để đánh giá cuối cùng.
  4. Mọi bộ biến đổi thống kê (mean/median theo category, scaler, encoder) chỉ được `fit` trên **Train Split** và `transform` sang Validation/Test.

---

## 5.3. Thiết kế Đường ống Thời gian Thực (Kafka Streaming Pipeline)

Đường ống Streaming được kích hoạt ở giai đoạn mở rộng sau khi Batch Pipeline đã vận hành ổn định:

```text
Transaction Simulator (scripts/simulate_transactions.py)
  (Đọc tuần tự từ fraudTest.csv, ẩn cột is_fraud khỏi payload sự kiện)
        |
        v
Kafka Producer
        |
        v
Kafka Topic: transactions (Partitioned by cc_num để giữ đúng thứ tự sự kiện trên từng thẻ)
        |
        v
Python Streaming Consumer
        |
        +---> [1. Validate & Deduplicate] (Kiểm tra schema JSON & chống trùng trans_num)
        |       |--> Nếu lỗi định dạng --> Đẩy vào Dead-Letter Queue (DLQ) / raw_transactions
        |
        +---> [2. State Lookup & Feature Calculation]
        |       (Truy vấn lịch sử 24h gần nhất của cc_num từ PostgreSQL core.transactions
        |        thông qua index idx_core_tx_card_unixtime để tính velocity & implied_speed_kmh)
        |
        +---> [3. Real-time Fraud Scoring]
        |       (Chạy Rule Engine + ML Model --> tính risk_score, risk_level, alert_reason)
        |
        +---> [4. Persist to PostgreSQL]
        |       (Ghi vào core.transactions, core.transaction_features, core.fraud_predictions,
        |        core.fraud_alerts và cập nhật tầng analytics)
        |
        v
FastAPI Backend (SSE /api/v1/stream/events hoặc WebSocket)
        |
        v
React Dashboard (Trang 4: Live Monitoring cập nhật tức thời)
```

### Các Yêu cầu Kỹ thuật Bắt buộc cho Luồng Streaming

1. **Định danh sự kiện duy nhất (`trans_num`):** Mỗi sự kiện phát đi từ Simulator đều mang `trans_num` duy nhất cùng `event_time` (`trans_date_trans_time`) và `ingested_at`.
2. **Đảm bảo Thứ tự theo Thẻ (Per-Card Ordering):** Kafka Producer sử dụng `cc_num` làm **Partition Key** để mọi giao dịch của cùng một thẻ tín dụng luôn đi vào cùng một partition và được xử lý đúng thứ tự thời gian.
3. **Xử lý Lặp sự kiện (At-least-once & Idempotent Consumer):** Nếu Consumer khởi động lại và đọc trùng message, cơ chế `ON CONFLICT (trans_num) DO NOTHING` tại PostgreSQL đảm bảo không ghi đè hoặc nhân đôi giao dịch.
4. **Cô lập Tin nhắn Lỗi (Poison Pill Isolation):** Các message sai định dạng JSON hoặc thiếu trường bắt buộc được bắt ngoại lệ, ghi vào bảng `raw.raw_transactions` với `is_valid = FALSE` để hiển thị trên trang giám sát mà **không làm sập tiến trình Consumer**.
5. **Theo dõi Độ trễ (Observability Metrics):** Consumer ghi nhận độ trễ xử lý (`processing_latency_ms = scored_at - ingested_at`) và độ trễ hàng đợi (`consumer_lag`) để cung cấp cho API giám sát pipeline.
6. **Đồng nhất Logic Nghiệp vụ (Batch–Streaming Parity):** Cả Batch Pipeline và Streaming Consumer đều gọi chung các hàm chuẩn hóa trong `preprocessing/cleaner.py`, hàm trích xuất đặc trưng trong `preprocessing/feature_engineering.py` và bộ chấm điểm trong `src/fraud_detection/inference/predictor.py`.
