# Transaction Fraud Detection Platform

Dự án phát hiện gian lận giao dịch (Transaction Fraud Detection) kết hợp pipeline tiền xử lý dữ liệu bảng & chuỗi thời gian, huấn luyện/đánh giá mô hình Machine Learning, lưu trữ cơ sở dữ liệu và tích hợp ứng dụng (FastAPI & Dashboard UI).

## Cấu trúc thư mục

```text
Transaction-Fraud-Detection-Platform/
├── configs/                        # File cấu hình chung (YAML)
│   └── config.yaml
├── docs/                           # Tài liệu dự án (kiến trúc, từ điển dữ liệu...)
│   ├── architecture.md
│   └── data_dictionary.md
├── data/                           # Lưu trữ dữ liệu (raw, interim, processed)
│   ├── raw/
│   ├── interim/
│   └── processed/
├── database/                       # Quản lý Cơ sở dữ liệu (lưu giao dịch, kết quả dự đoán, cảnh báo)
│   ├── connection.py
│   ├── models.py
│   ├── repository.py
│   ├── schema.sql
│   └── migrations/
├── preprocessing/                  # Pipeline tiền xử lý dữ liệu & Feature Engineering
│   ├── loader.py
│   ├── cleaner.py
│   ├── splitter.py
│   ├── feature_engineering.py
│   └── pipeline.py
├── src/                            # Modeling, Training, Inference & Evaluation
│   └── fraud_detection/
│       ├── config.py
│       ├── models/
│       ├── training/
│       ├── inference/
│       ├── evaluation/
│       └── utils/
├── app/                            # Ứng dụng tích hợp (FastAPI & UI Dashboard)
│   ├── api/
│   └── ui/
├── notebooks/                      # Jupyter Notebooks khám phá & thử nghiệm
├── models/                         # Lưu trữ model artifacts sau huấn luyện
├── reports/                        # Biểu đồ (figures) và kết quả đánh giá (metrics)
├── scripts/                        # Các script chạy pipeline từ CLI
└── tests/                          # Unit tests
```
