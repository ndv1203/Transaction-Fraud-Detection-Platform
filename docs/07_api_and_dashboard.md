# 07. Đặc tả Backend API & Giao diện Dashboard (API & Dashboard Specification)

Tài liệu này quy định thiết kế chi tiết cho hệ thống **Backend API (FastAPI)** và **Frontend Dashboard 6 chuyên trang (React + TypeScript + Apache ECharts / Recharts)**, được thiết kế riêng cho cấu trúc dữ liệu **Sparkov Credit Card Fraud**.

---

## 7.1. Đặc tả Giao diện Dashboard 6 Chuyên trang (React + TypeScript)

Hệ thống giao diện người dùng được chia thành **6 trang chuyên biệt**, phục vụ đúng nhu cầu của từng nhóm đối tượng (Manager, Data Analyst, Fraud Analyst, Data Engineer).

> **Nguyên tắc Hiển thị Quan trọng:** Mọi biểu đồ và thẻ KPI phải phân biệt rõ ràng giữa **Giao dịch Nghi ngờ / Bị gắn cờ (`Suspicious / Flagged Transactions` — do hệ thống dự đoán)** và **Giao dịch Gian lận Đã xác nhận (`Confirmed Fraud` — từ nhãn thực tế `transaction_labels` hoặc sau khi Fraud Analyst xác minh)**.

---

### Trang 1: Tổng quan Điều hành (Executive Overview)

- **Mục đích:** Cung cấp bức tranh toàn cảnh về lưu lượng giao dịch, giá trị thanh toán và tình hình rủi ro gian lận cho cấp quản lý.
- **Bộ thẻ KPI (KPI Cards):**
  1. `Total Transactions`: Tổng số lượng giao dịch đã xử lý.
  2. `Total Transaction Volume ($)`: Tổng giá trị giao dịch (USD).
  3. `Suspicious Transactions`: Số giao dịch bị gắn cờ nghi ngờ (`is_flagged = TRUE`).
  4. `Confirmed Fraud Transactions`: Số giao dịch gian lận đã được xác nhận (`is_confirmed_fraud = TRUE`).
  5. `Suspicious Amount ($)`: Tổng giá trị tiền (USD) nằm trong các giao dịch nghi ngờ.
  6. `Suspicious Rate vs Confirmed Fraud Rate (%)`: Tỷ lệ nghi ngờ (%) đặt cạnh tỷ lệ gian lận thực tế (%).
- **Hệ thống Biểu đồ:**

| Tên biểu đồ | Loại biểu đồ (ECharts / Recharts) | Nội dung hiển thị |
| :--- | :--- | :--- |
| **Transaction Volume & Amount Over Time** | Dual-axis Line / Bar Chart | Số lượng giao dịch và tổng tiền (USD) theo giờ/ngày/tháng. |
| **Normal vs Suspicious vs Confirmed Fraud** | Donut Chart | Tỷ trọng phân bổ giao dịch theo trạng thái rủi ro. |
| **Transactions by Spending Category** | Horizontal Bar Chart | Phân bố lưu lượng trên 14 danh mục `category` (`grocery_pos`, `shopping_net`, `gas_transport`...). |
| **Suspicious Amount by Category ($)** | Bar Chart | Tổng số tiền nghi ngờ gian lận (USD) theo từng `category`. |
| **Suspicious & Confirmed Fraud Rate Trend** | Multi-line Chart | Diễn biến tỷ lệ nghi ngờ và tỷ lệ gian lận qua thời gian. |

- **Bộ lọc toàn trang (Global Filters):** Khoảng thời gian (`start_date`, `end_date`), Danh mục chi tiêu (`category`), Bang (`state_code`), Mức độ rủi ro (`risk_level`: `LOW`, `MEDIUM`, `HIGH`), Phương pháp phát hiện (`detection_method`: `RULE_BASED`, `ML_MODEL`).

---

### Trang 2: Phân tích Giao dịch Chuyên sâu (Transaction Analytics)

- **Mục đích:** Giúp Data Analyst khám phá phân phối giao dịch, hành vi chi tiêu của chủ thẻ và cấu trúc danh mục cửa hàng.
- **Các biểu đồ & Bảng phân tích:**
  - **Phân phối số tiền giao dịch (`amt` & `log(1 + amt)`):** Biểu đồ Histogram & KDE distribución.
  - **Số lượng & Giá trị trung bình/trung vị theo `category`:** Grouped Bar Chart so sánh 14 danh mục chi tiêu.
  - **Phân tích Ngoại lai (Outlier Analysis):** Box Plot phân phối `amt` theo từng `category` (cắt ngưỡng P99.5 để trực quan hóa rõ ràng).
  - **Hoạt động theo Thẻ (`cc_num`) & Cửa hàng (`merchant`):** Top các thẻ có tần suất quẹt cao nhất và các cửa hàng có doanh số lớn nhất.
  - **Phân bố Địa lý theo Bang (`state_code`):** Biểu đồ Choropleth / Bar Chart lưu lượng giao dịch và dân số đô thị (`city_pop`).

---

### Trang 3: Phân tích Chuyên sâu Gian lận (Fraud Analytics)

- **Mục đích:** So sánh đặc trưng hành vi giữa giao dịch hợp lệ và giao dịch gian lận/nghi ngờ để tinh chỉnh luật và mô hình.
- **Các biểu đồ & Bảng phân tích:**
  - **Số lượng & Tổng tiền giao dịch nghi ngờ theo thời gian:** Area / Line Chart.
  - **Tỷ lệ Gian lận / Nghi ngờ theo Danh mục (`category`):** Horizontal Bar Chart làm nổi bật các nhóm rủi ro cao (`shopping_net`, `misc_net`, `grocery_pos`).
  - **Phân bố theo Khung giờ trong ngày (`00h–23h`):** Line Chart đánh dấu vùng rủi ro cao ban đêm (`22:00–03:59`).
  - **Heatmap Tương tác `Category × Hour of Day` và `Weekday × Hour of Day`:** Ma trận nhiệt chỉ rõ khung giờ và danh mục nào bị tấn công mạnh nhất.
  - **So sánh Phân phối Đặc trưng (`Flagged/Fraud` vs `Normal`):**
    - Phân phối vận tốc di chuyển `implied_speed_kmh` (*Impossible Travel*).
    - Phân phối tần suất quẹt thẻ `tx_count_24h` và tổng chi tiêu `amt_sum_24h` (*Fraud Burst*).
    - Tỷ lệ gian lận theo nhóm tuổi chủ thẻ (`<25`, `25–35`, `35–50`, `50–65`, `65+`).
  - **Phân bố Mức độ Rủi ro (`risk_level`):** Biểu đồ tỷ lệ `LOW`, `MEDIUM`, `HIGH`.

---

### Trang 4: Giám sát Cận Thời gian Thực (Live Monitoring)

- **Mục đích:** Theo dõi trực tiếp luồng giao dịch đang chảy qua Kafka và phát hiện cảnh báo tức thời.
- **Các thành phần hiển thị:**
  - **KPI Phiên hiện tại:** Số giao dịch nhận được trong phiên, số giao dịch nghi ngờ trong cửa sổ 5–15 phút gần nhất, tổng số tiền nghi ngờ (USD), độ trễ xử lý trung bình (`ms`).
  - **Biểu đồ Lưu lượng Trực tiếp (Live Throughput Chart):** Biểu đồ đường trượt theo thời gian thực (cập nhật mỗi giây/mỗi lô sự kiện).
  - **Bảng Cảnh báo Mới nhất (Recent High-Risk Alerts):** Danh sách các giao dịch `HIGH` / `MEDIUM` vừa phát sinh kèm nút bấm chuyển nhanh sang trang Điều tra.
  - **Luồng Giao dịch Đang đến (Live Incoming Transaction Feed):** Bảng cuộn tự động hiển thị `trans_num`, `event_time`, `cc_num` (che một phần), `merchant`, `category`, `amt`, `risk_score`, `risk_level`.
  - **Trạng thái Kết nối Stream:** Đèn báo trạng thái SSE/WebSocket (`CONNECTED`, `RECONNECTING`, `DISCONNECTED`) kèm cơ chế tự động kết nối lại (Exponential Backoff Reconnection).

---

### Trang 5: Điều tra Giao dịch & Cảnh báo (Transaction Investigation)

- **Mục đích:** Cung cấp đầy đủ ngữ cảnh để Fraud Analyst thẩm định một giao dịch đáng ngờ và ra quyết định xác nhận (`CONFIRMED_FRAUD` hoặc `FALSE_POSITIVE`).
- **Thông tin hiển thị khi chọn một giao dịch / cảnh báo:**
  1. **Chi tiết Giao dịch (Transaction Profile):**
     - `trans_num`, `transaction_id`, trạng thái cảnh báo (`alert_status`).
     - Thời gian sự kiện (`event_time`), thời gian hệ thống nhận (`ingested_at`), thời gian chấm điểm (`predicted_at`).
     - Số tiền (`amt`), Danh mục (`category`), Cửa hàng (`merchant`), Tọa độ điểm quẹt (`merch_lat`, `merch_lon`).
  2. **Hồ sơ Thẻ & Chủ thẻ (Cardholder Context):**
     - Mã thẻ `cc_num`, Giới tính (`gender`), Tuổi (`customer_age`), Nghề nghiệp (`job`), Thành phố & Bang cư trú (`city`, `state_code`), Tọa độ nhà (`lat`, `lon`).
  3. **Điểm Rủi ro & Giải thích (Explainable Risk Breakdown):**
     - `risk_score`, `risk_level`, `detection_method`, `model_version`.
     - Danh sách các quy tắc bị kích hoạt (`R001`–`R006`) hoặc các đặc trưng đóng góp lớn nhất (`amt_to_card_mean_ratio`, `implied_speed_kmh`, `tx_count_24h`...).
  4. **Lịch sử Quẹt thẻ Gần nhất & Bản đồ Di chuyển (Card Activity Timeline & Geo Trajectory):**
     - Bảng chuỗi các giao dịch của cùng thẻ `cc_num` trong 24 giờ trước đó (giúp nhìn rõ hiện tượng *Fraud Burst* hoặc *Card Testing*).
     - Biểu đồ mạng lưới / bản đồ đường đi giữa các cửa hàng (`Card` $\leftrightarrow$ `Merchants`) để trực quan hóa khoảng cách `merch_to_merch_dist_km` và vận tốc `implied_speed_kmh`. *(Lưu ý: Các liên kết đồ thị được dùng làm tín hiệu hỗ trợ điều tra, không phải bằng chứng kết luận tự động).*
  5. **Thao tác Nghiệp vụ (Investigation Actions):**
     - Cho phép Analyst cập nhật trạng thái cảnh báo (`INVESTIGATING` $\rightarrow$ `CONFIRMED_FRAUD` / `FALSE_POSITIVE`) và lưu ghi chú điều tra (`reviewer_notes`).

---

### Trang 6: Chất lượng Dữ liệu & Giám sát Pipeline (Data Quality & Pipeline Monitoring)

- **Mục đích:** Giúp Data Engineer giám sát sức khỏe đường ống dữ liệu Batch và Streaming.
- **Các chỉ số KPI Giám sát:**

| Chỉ số (Metric) | Ý nghĩa hiển thị |
| :--- | :--- |
| **Total Records Ingested** | Tổng số bản ghi đã tiếp nhận vào tầng `raw`. |
| **Valid Records (`accepted_count`)** | Số bản ghi vượt qua kiểm định Pandera thành công. |
| **Invalid Records (`rejected_count`)** | Số bản ghi bị từ chối do vi phạm schema hoặc quy tắc nghiệp vụ. |
| **Duplicate Records Detected** | Số bản ghi trùng mã giao dịch `trans_num` bị chặn lại. |
| **Missing-Value / Schema Error Rate (%)** | Tỷ lệ bản ghi có giá trị khuyết hoặc sai định dạng. |
| **Batch Pipeline Latency (s)** | Thời gian thực thi của đợt chạy Batch gần nhất. |
| **Last Successful Batch** | Mã `batch_id` và thời điểm hoàn thành của lô nạp thành công gần nhất. |
| **Kafka Consumer Lag & Stream Latency** | Độ trễ tin nhắn chưa đọc trên Kafka và thời gian xử lý trung bình mỗi sự kiện (`ms`). |

- **Bảng Lịch sử Chạy Pipeline (`raw.ingestion_batches`):**
  - Hiển thị `batch_id`, `source_name`, `started_at`, `completed_at`, `input_count`, `accepted_count`, `rejected_count`, `status` (`RUNNING`, `SUCCEEDED`, `FAILED`) và nút xem chi tiết `error_summary` JSON.

---

## 7.2. Đặc tả Backend REST API (FastAPI Specification)

Toàn bộ API được đặt tiền tố phiên bản `/api/v1` và cài đặt tại `app/api/routes.py`.

### Danh mục Endpoints Chuẩn

| Phương thức | Endpoint | Mục đích & Chức năng |
| :--- | :--- | :--- |
| `GET` | `/api/v1/dashboard/overview` | Trả về các thẻ KPI tổng quan cho Trang 1 (hỗ trợ lọc theo ngày, `category`, `state_code`, `risk_level`). |
| `GET` | `/api/v1/dashboard/transactions/trend` | Chuỗi thời gian số lượng và tổng tiền giao dịch theo khoảng chia (`hour`, `day`, `month`). |
| `GET` | `/api/v1/dashboard/fraud/trend` | Chuỗi thời gian số lượng giao dịch nghi ngờ, gian lận xác nhận và tỷ lệ rủi ro. |
| `GET` | `/api/v1/dashboard/fraud/distribution` | Thống kê phân bố gian lận/nghi ngờ theo `category`, `hour_of_day`, `age_group`, `risk_level` và heatmap. |
| `GET` | `/api/v1/transactions` | Danh sách giao dịch có phân trang (`page`, `page_size`), sắp xếp và lọc đa điều kiện. |
| `GET` | `/api/v1/transactions/{trans_num}` | Chi tiết một giao dịch, kèm hồ sơ thẻ, các đặc trưng đã tính (`transaction_features`), lịch sử 24h của thẻ và điểm dự đoán. |
| `GET` | `/api/v1/fraud/alerts` | Danh sách cảnh báo gian lận có phân trang, lọc theo `alert_status`, `risk_level`, `detection_method`. |
| `GET` | `/api/v1/fraud/alerts/{alert_id}` | Chi tiết cảnh báo, giải thích các quy tắc kích hoạt (`alert_reason`) và các giao dịch liên quan của cùng `cc_num`. |
| `PATCH` | `/api/v1/fraud/alerts/{alert_id}` | Cập nhật trạng thái điều tra (`INVESTIGATING`, `CONFIRMED_FRAUD`, `FALSE_POSITIVE`) và ghi chú của Analyst. |
| `POST` | `/api/v1/fraud/score` | Endpoint chấm điểm trực tiếp 1 giao dịch mới (phục vụ kiểm thử nhanh hoặc tích hợp dịch vụ). |
| `GET` | `/api/v1/pipeline/runs` | Lịch sử các đợt chạy nạp dữ liệu từ bảng `raw.ingestion_batches`. |
| `GET` | `/api/v1/data-quality/summary` | Tổng hợp các chỉ số chất lượng dữ liệu, tỷ lệ lỗi và thống kê nguyên nhân từ chối bản ghi. |
| `GET` | `/api/v1/stream/events` | Luồng **Server-Sent Events (SSE)** đẩy các giao dịch mới và cảnh báo thời gian thực lên Trang 4 (*Live Monitoring*). |

### Ví dụ Truy vấn (Query Example)

```http
GET /api/v1/dashboard/fraud/trend?start_date=2020-06-21&end_date=2020-12-31&interval=day&category=shopping_net&detection_method=HYBRID HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Yêu cầu Kỹ thuật đối với Tầng API

1. **Tổng hợp tại SQL / Backend (Server-side Aggregation):** Tuyệt đối không tải hàng trăm nghìn bản ghi giao dịch thô xuống trình duyệt để tính tổng trên Frontend; mọi biểu đồ trên Dashboard phải gọi các API đã được tổng hợp sẵn qua tầng `analytics.*` của PostgreSQL.
2. **Phân trang Bắt buộc (Pagination):** Các endpoint trả về danh sách (`/transactions`, `/fraud/alerts`, `/pipeline/runs`) phải giới hạn `page_size` (mặc định `50`, tối đa `200`).
3. **Kiểm tra Đầu vào bằng Pydantic (`app/api/schemas.py`):** Xác thực chặt chẽ định dạng ngày tháng, các giá trị enum (`risk_level`, `alert_status`, `interval`) và trả về cấu trúc lỗi JSON thống nhất kèm mã HTTP chuẩn (`400`, `404`, `422`, `500`).
