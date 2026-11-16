# Tài liệu Dự án — Transaction Fraud Detection Platform

Chào mừng bạn đến với bộ tài liệu kỹ thuật của **Transaction Fraud Detection Platform** — nền tảng phân tích dữ liệu giao dịch tài chính và giám sát gian lận thẻ tín dụng theo kiến trúc **Hybrid Batch Analytics & Near Real-time Transaction Monitoring**.

Tài liệu được thiết kế theo cấu trúc phân tách thành **8 phần chuyên biệt** để dễ tra cứu, bảo trì và đối chiếu trực tiếp với mã nguồn trong repository.

---

## Danh mục Tài liệu (`docs/`)

| STT | File tài liệu | Nội dung chính | Đối tượng đọc chính |
| :--- | :--- | :--- | :--- |
| **01** | [01_overview.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/docs/01_overview.md) | Tầm nhìn dự án, mục tiêu, đối tượng người dùng, phạm vi (In/Out of scope) và câu chuyện xuyên suốt của dữ liệu (Product Narrative). | Mọi thành viên, Manager, Product |
| **02** | [02_architecture.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/docs/02_architecture.md) | Kiến trúc hệ thống tổng thể (Batch + Kafka Streaming), Tech Stack chi tiết và cấu trúc thư mục dự án. | Data Engineer, Backend/Frontend Dev |
| **03** | [03_data_dictionary.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/docs/03_data_dictionary.md) | Chiến lược dữ liệu **Sparkov Credit Card Fraud**, quy tắc chuẩn hóa 22 trường gốc, chống rò rỉ dữ liệu (Leakage Prevention) và danh mục đặc trưng (Feature Catalog). | Data Analyst, Data Scientist, Data Engineer |
| **04** | [04_database_design.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/docs/04_database_design.md) | Thiết kế PostgreSQL 3 tầng (`raw`, `core`, `analytics`), Star Schema cho Dashboard, định nghĩa bảng/cột chi tiết và quy tắc kỹ thuật DB. | Data Engineer, Backend Dev |
| **05** | [05_pipelines_and_eda.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/docs/05_pipelines_and_eda.md) | Thiết kế Batch ETL/ELT Pipeline, Kafka Streaming Pipeline, kiểm định chất lượng dữ liệu (Pandera) và kết quả phân tích khám phá (EDA Insights từ Sparkov). | Data Engineer, Data Analyst |
| **06** | [06_fraud_detection.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/docs/06_fraud_detection.md) | Thiết kế hệ thống phát hiện gian lận: Tập luật nghiệp vụ giải thích được (Rule-based R001–R006), công thức Risk Scoring, ML Baseline và chiến lược đánh giá Out-of-Time. | Fraud Analyst, Data Scientist |
| **07** | [07_api_and_dashboard.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/docs/07_api_and_dashboard.md) | Đặc tả REST API + SSE/WebSocket (FastAPI) và đặc tả 6 trang giao diện Dashboard (React + TypeScript + Apache ECharts/Recharts). | Backend Dev, Frontend Dev, Fraud Analyst |
| **08** | [08_roadmap_and_standards.md](file:///home/nam/Desktop/Transaction-Fraud-Detection-Platform/docs/08_roadmap_and_standards.md) | Lộ trình triển khai 10 tuần, Definition of Done (DoD) từng giai đoạn, 10 tiêu chuẩn kỹ thuật (Engineering Quality), phân bổ nguồn lực và checklist Sprint 0. | Mọi thành viên, Project Lead |

---

## Điểm nhấn Kiến trúc & Dữ liệu đã thống nhất

1. **Bộ dữ liệu chuẩn (MVP Dataset)**: Sử dụng bộ dữ liệu **Sparkov Credit Card Fraud Detection** (`fraudTrain.csv` gồm `1,296,675` giao dịch từ `01/2019` đến `06/2020` và `fraudTest.csv` gồm `555,719` giao dịch từ `06/2020` đến `12/2020`), có đầy đủ dấu thời gian thực (`trans_date_trans_time`, `unix_time`), định danh thẻ (`cc_num`), cửa hàng (`merchant`, `category`), tọa độ địa lý (`lat`, `lon`, `merch_lat`, `merch_lon`) và nhân khẩu học (`dob`, `job`, `city_pop`).
2. **Chuẩn hóa Schema đồng nhất**: Đổi tên 3 cột gốc trùng từ khóa SQL ngay từ tầng làm sạch (`state` $\rightarrow$ `state_code`, `long` $\rightarrow$ `lon`, `merch_long` $\rightarrow$ `merch_lon`) và loại bỏ các cột định danh cá nhân gây nhiễu (`Unnamed: 0`, `first`, `last`, `street`) khi đưa vào mô hình.
3. **Cơ sở dữ liệu PostgreSQL 3 tầng**:
   - `raw`: Lưu nguyên trạng payload gốc (`JSONB`) và lịch sử các đợt nạp (`ingestion_batches`).
   - `core`: Lưu thực thể chuẩn hóa (`cards`, `merchants`, `transactions`), tách biệt hoàn toàn bảng nhãn thực tế (`transaction_labels`), bảng đặc trưng (`transaction_features`), dự đoán (`fraud_predictions`) và cảnh báo điều tra (`fraud_alerts`).
   - `analytics`: Mô hình Star Schema (`fact_transactions`, `dim_time`, `dim_cards`, `dim_merchants`, `dim_categories`) cùng các bảng/view tổng hợp phục vụ truy vấn tốc độ cao cho Dashboard.
4. **Kiến trúc Hybrid (Batch + Near Real-time)**: Ưu tiên hoàn thiện luồng Batch ETL/ELT và kiểm định chất lượng dữ liệu trước; sau đó mở rộng luồng giả lập giao dịch thời gian thực qua **Apache Kafka** $\rightarrow$ **Python Consumer** $\rightarrow$ **PostgreSQL** $\rightarrow$ **FastAPI (SSE/WebSocket)** $\rightarrow$ **React Dashboard**.
