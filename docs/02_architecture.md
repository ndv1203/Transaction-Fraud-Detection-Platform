# 02. Kiến trúc Hệ thống & Công nghệ (System Architecture & Tech Stack)

Tài liệu này mô tả kiến trúc logic tổng thể của nền tảng, danh mục công nghệ sử dụng và cấu trúc tổ chức mã nguồn trong repository.

---

## 2.1. Kiến trúc Logic Tổng thể (Logical Architecture)

Hệ thống được thiết kế theo mô hình **Hybrid Data Architecture**, kết hợp đường ống xử lý theo lô (Batch Pipeline) cho dữ liệu lịch sử **Sparkov** và đường ống xử lý sự kiện (Streaming Pipeline) qua **Apache Kafka** cho luồng giao dịch phát sinh cận thời gian thực.

```text
                                 DATA SOURCES
               +----------------------+----------------------+
               |                                             |
     Sparkov Credit Card CSV                      Transaction Simulator
   (fraudTrain.csv / fraudTest.csv)             (Real-time Event Generator)
               |                                             |
         Batch Ingestion                              Kafka Producer
               |                                             |
               v                                             v
       RAW DATA LAYER (raw.*)  <------------------  Kafka Topic: transactions
     (ingestion_batches, raw_transactions)                   |
               |                                             |
               +----------------------+----------------------+
                                      |
                                      v
                           VALIDATION & PROCESSING
               (Pandera Schema Check / Deduplication / Cleaning)
               (Standardize: state -> state_code, long -> lon)
                                      |
                                      v
                            CORE DATA LAYER (core.*)
            (cards, merchants, transactions, transaction_labels)
                                      |
                                      v
                              FEATURE ENGINEERING
             (1h/6h/24h Card Velocity, Haversine Distance, Speed,
                    Category Ratios, Demographic Features)
                                      |
                         (core.transaction_features)
                                      |
                    +-----------------+-----------------+
                    |                                   |
                    v                                   v
             FRAUD DETECTION                     ANALYTICS SQL
       (Rule Engine + ML Baseline)          (Star Schema & Aggregations)
     (predictions & fraud_alerts)                       |
                    |                                   |
                    +-----------------+-----------------+
                                      |
                                      v
                        ANALYTICS DATA LAYER (analytics.*)
              (fact_transactions, dim_time, dim_cards, dim_merchants,
               dim_categories, agg_hourly_tx, agg_daily_fraud, ...)
                                      |
                                      v
                               FASTAPI BACKEND
                        (REST API v1 + SSE / WebSocket)
                                      |
                                      v
                         REACT + TYPESCRIPT DASHBOARD
                 (1. Executive Overview | 2. Transaction Analytics
                  3. Fraud Analytics    | 4. Live Monitoring
                  5. Investigation      | 6. Data Quality & Pipeline)
```

---

## 2.2. Danh mục Công nghệ Đề xuất (Technology Stack)

| Phân hệ (Area) | Công nghệ (Technology) | Vai trò & Trách nhiệm (Responsibility) |
| :--- | :--- | :--- |
| **Data Ingestion** | Python (`pandas`, `pyarrow`) | Đọc dữ liệu nguồn CSV, xuất/đọc Parquet trung gian và nạp vào tầng `raw`. |
| **Batch Processing** | Pandas, NumPy, SQL | Làm sạch, chuẩn hóa tên cột, ép kiểu tối ưu bộ nhớ và tính toán đặc trưng hàng loạt. |
| **Data Validation** | Pandera | Kiểm tra hợp lệ schema, kiểu dữ liệu, miền giá trị và phát hiện bản ghi vi phạm quy tắc nghiệp vụ. |
| **Streaming** | Apache Kafka (`confluent-kafka` / `kafka-python`) | Vận chuyển sự kiện giao dịch giả lập theo thời gian thực từ Simulator tới Consumer. |
| **Database** | PostgreSQL | Lưu trữ hợp nhất trên 3 schema: `raw` (nguyên bản), `core` (tác vụ & phát hiện), `analytics` (Star Schema). |
| **Transformation** | SQL (tùy chọn mở rộng `dbt`) | Xây dựng các bảng Fact, Dimension và các bảng/view tổng hợp cho Dashboard. |
| **Fraud Detection** | Python, `scikit-learn`, `lightgbm` / `xgboost` | Kết hợp bộ quy tắc nghiệp vụ (Rule Engine) và mô hình học máy cơ sở (ML Baseline). |
| **Backend API** | FastAPI, SQLAlchemy, Pydantic | Cung cấp RESTful API phân trang, lọc dữ liệu và luồng sự kiện trực tiếp qua SSE / WebSocket. |
| **Frontend UI** | React, TypeScript, TailwindCSS | Giao diện người dùng 6 chuyên trang phục vụ Analyst, Engineer và Manager. |
| **Visualization** | Apache ECharts hoặc Recharts | Hiển thị biểu đồ chuỗi thời gian, phân phối, heatmap và đồ thị mạng lưới giao dịch. |
| **Deployment** | Docker & Docker Compose | Đóng gói và khởi chạy môi trường đa dịch vụ đồng nhất tại máy cục bộ (Local Environment). |

> **Nguyên tắc triển khai tuần tự:** Khởi đầu bằng việc xây dựng **Batch Pipeline + PostgreSQL + FastAPI + Dashboard** thật vững chắc và chính xác. Sau khi luồng Batch hoạt động ổn định, mới bổ sung **Kafka + Transaction Simulator** ở giai đoạn tiếp theo. Không cần sử dụng Spark, Hadoop hay Data Lake riêng biệt cho phạm vi MVP này.

---

## 2.3. Cấu trúc Thư mục Dự án (Repository Structure)

Cấu trúc repository kết hợp hài hòa giữa các module Python hiện có và kiến trúc mở rộng đầy đủ (Full-stack Monorepo):

```text
Transaction-Fraud-Detection-Platform/
├── configs/                        # Cấu hình tập trung của hệ thống
│   └── config.yaml                 # Đường dẫn, danh sách cột chuẩn hóa, siêu tham số, DB URL
│
├── docs/                           # Bộ tài liệu kỹ thuật chia theo 8 chuyên đề
│   ├── README.md                   # Mục lục điều hướng tài liệu
│   ├── 01_overview.md              # Tổng quan, mục tiêu, phạm vi dự án
│   ├── 02_architecture.md          # Kiến trúc hệ thống & Tech Stack
│   ├── 03_data_dictionary.md       # Từ điển dữ liệu Sparkov & Danh mục đặc trưng
│   ├── 04_database_design.md       # Thiết kế PostgreSQL 3 tầng (raw, core, analytics)
│   ├── 05_pipelines_and_eda.md     # Thiết kế Batch/Streaming Pipeline & Báo cáo EDA
│   ├── 06_fraud_detection.md       # Thiết kế Rule Engine, Risk Scoring & ML Baseline
│   ├── 07_api_and_dashboard.md     # Đặc tả FastAPI Endpoints & 6 trang React Dashboard
│   └── 08_roadmap_and_standards.md # Lộ trình 10 tuần, DoD, Tiêu chuẩn kỹ thuật & Sprint 0
│
├── data/                           # Lưu trữ dữ liệu cục bộ (được ignore khỏi Git trừ .gitkeep)
│   ├── raw/                        # Chứa fraudTrain.csv và fraudTest.csv gốc
│   ├── interim/                    # Chứa train_cleaned.parquet, test_cleaned.parquet
│   ├── processed/                  # Dữ liệu đã trích xuất đặc trưng sẵn sàng cho ML
│   └── reports/                    # Báo cáo kiểm định chất lượng dữ liệu (Data Quality JSON/CSV)
│
├── notebooks/                      # Jupyter Notebooks phục vụ khám phá & thử nghiệm
│   └── 01_eda.ipynb                # Notebook EDA toàn diện bộ dữ liệu Sparkov (Hỗ trợ Local & Colab)
│
├── preprocessing/                  # Pipeline tiền xử lý dữ liệu, kiểm định & tạo đặc trưng
│   ├── loader.py                   # Đọc CSV tối ưu bộ nhớ, lưu/đọc Parquet
│   ├── cleaner.py                  # Đổi tên cột (state_code, lon, merch_lon), lọc cột thừa, chuẩn hóa
│   ├── validation.py               # Kiểm định chất lượng dữ liệu bằng Pandera
│   ├── splitter.py                 # Chia tập Train / Out-of-Time Validation / Test chống rò rỉ
│   ├── feature_engineering.py      # Trích xuất đặc trưng thời gian, khoảng cách, tốc độ, velocity
│   └── pipeline.py                 # Điều phối toàn bộ luồng tiền xử lý Batch & Streaming
│
├── database/                       # Quản lý Cơ sở dữ liệu PostgreSQL
│   ├── connection.py               # Quản lý kết nối SQLAlchemy / Session pool
│   ├── models.py                   # Định nghĩa ORM Models cho các schema raw, core, analytics
│   ├── repository.py               # Các hàm truy vấn, ghi nhận lô nạp, lưu dự đoán & cảnh báo
│   ├── schema.sql                  # DDL khởi tạo schemas, tables, indexes và views
│   └── migrations/                 # Quản lý phiên bản thay đổi cấu trúc DB (Alembic / SQL scripts)
│
├── src/                            # Lõi phát hiện gian lận (Rules, ML Models, Training, Inference)
│   └── fraud_detection/
│       ├── config.py               # Đọc và xác thực cấu hình hệ thống
│       ├── rules/                  # Tập luật phát hiện gian lận có giải thích (R001 - R006)
│       ├── models/                 # Định nghĩa các mô hình ML Baseline (Logistic Regression, RF, LGBM)
│       ├── training/               # Huấn luyện mô hình, tinh chỉnh ngưỡng (Threshold Tuning)
│       ├── inference/              # Chấm điểm rủi ro kết hợp Rules + ML và sinh lý do cảnh báo
│       ├── evaluation/             # Tính toán PR-AUC, F1, Recall, Confusion Matrix
│       └── utils/                  # Logger và các tiện ích dùng chung
│
├── app/                            # Tầng ứng dụng tích hợp (Backend API & Frontend Dashboard)
│   ├── api/                        # FastAPI Backend
│   │   ├── main.py                 # Khởi tạo ứng dụng FastAPI, CORS, middlewares
│   │   ├── routes.py               # Các endpoints /api/v1/dashboard, /transactions, /fraud, /pipeline
│   │   ├── schemas.py              # Pydantic request/response schemas
│   │   └── dependencies.py         # Dependency injection (DB session, Predictor instance)
│   └── ui/                         # Giao diện người dùng (React + TypeScript Dashboard / Prototype UI)
│
├── scripts/                        # Các kịch bản chạy từ dòng lệnh (CLI Entrypoints)
│   ├── run_preprocessing.py        # Chạy pipeline làm sạch & nạp dữ liệu Batch
│   ├── run_training.py             # Chạy huấn luyện mô hình
│   ├── run_evaluation.py           # Chạy đánh giá mô hình và xuất báo cáo vào reports/
│   ├── simulate_transactions.py    # Giả lập bắn sự kiện giao dịch qua Kafka (Streaming Producer)
│   └── run_app.py                  # Khởi chạy dịch vụ API / Ứng dụng
│
├── reports/                        # Kết quả đầu ra phục vụ báo cáo
│   ├── figures/                    # Biểu đồ trích xuất từ EDA và đánh giá mô hình
│   └── metrics/                    # File JSON/CSV lưu kết quả đánh giá thực nghiệm
│
├── tests/                          # Kiểm thử tự động (Pytest)
│   ├── test_preprocessing.py       # Kiểm thử làm sạch, đổi tên cột, tạo đặc trưng không rò rỉ
│   ├── test_models.py              # Kiểm thử tập luật, mô hình và dự đoán
│   └── test_api.py                 # Kiểm thử các REST API endpoints
│
├── docker-compose.yml              # Khởi chạy PostgreSQL, Kafka, Backend API và Frontend Dashboard
├── pyproject.toml                  # Quản lý dependencies và cấu hình build với uv
└── README.md                       # Tài liệu giới thiệu nhanh ở thư mục gốc
```

### Nguyên tắc Phân tách Trách nhiệm (Separation of Concerns)

1. **`notebooks/` chỉ dùng để khám phá và chứng minh giả thuyết:** Mọi logic xử lý dữ liệu lặp lại được đều phải đóng gói thành hàm/class sạch sẽ trong `preprocessing/`.
2. **Độc lập giữa Ingestion, Detection và API:** Logic chấm điểm rủi ro (`src/fraud_detection/`) không phụ thuộc cứng vào FastAPI hay Kafka, giúp có thể gọi chung từ cả Batch Pipeline lẫn Streaming Consumer.
3. **Cấu hình hóa toàn bộ tham số (`configs/config.yaml`):** Không hard-code đường dẫn file, danh sách cột hay ngưỡng phân loại trong code xử lý.
