-- Initial SQL schema for Transaction Fraud Detection Platform (Sparkov Dataset)

-- 1. Bảng lưu dữ liệu giao dịch gốc (đã chuẩn hóa kiểu dữ liệu, chưa mã hóa ML)
-- Phục vụ: hiển thị trên Dashboard UI và truy vấn lịch sử giao dịch (1h/24h) cho từng thẻ (cc_num)
CREATE TABLE IF NOT EXISTS transactions (
    trans_num VARCHAR(64) PRIMARY KEY,
    trans_date_trans_time TIMESTAMP NOT NULL,
    unix_time BIGINT NOT NULL,
    cc_num VARCHAR(32) NOT NULL,
    merchant VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    amt REAL NOT NULL,
    gender VARCHAR(8),
    city VARCHAR(128),
    state_code VARCHAR(16),           -- Map từ cột 'state' (tránh trùng từ khóa STATE của SQL)
    zip VARCHAR(16),
    lat REAL,
    lon REAL,                         -- Map từ cột 'long' (tránh trùng từ khóa kiểu dữ liệu LONG của SQL)
    city_pop INTEGER,
    job VARCHAR(128),
    dob DATE,
    merch_lat REAL,
    merch_lon REAL,                   -- Map từ cột 'merch_long' cho đồng bộ với 'lon'
    is_fraud_actual INTEGER,          -- Nhãn thực tế (nếu có sau khi xác minh)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_cc_num_time
    ON transactions (cc_num, unix_time);

-- 2. Bảng lưu kết quả dự đoán gian lận & snapshot các đặc trưng đã xử lý
CREATE TABLE IF NOT EXISTS fraud_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trans_num VARCHAR(64) NOT NULL,
    fraud_probability REAL NOT NULL,
    is_fraud_predicted INTEGER NOT NULL,
    risk_level VARCHAR(16) NOT NULL,  -- LOW, MEDIUM, HIGH
    model_version VARCHAR(64),
    feature_snapshot TEXT,            -- JSON lưu các đặc trưng đã tính (VD: tx_count_24h, dist_km...)
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trans_num) REFERENCES transactions(trans_num)
);
