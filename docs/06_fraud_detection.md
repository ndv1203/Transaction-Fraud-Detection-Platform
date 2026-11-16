# 06. Thiết kế Hệ thống Phát hiện Gian lận (Fraud Detection Design)

Trong nền tảng này, phân hệ phát hiện gian lận (`src/fraud_detection/`) đóng vai trò tạo ra các tín hiệu cảnh báo có khả năng giải thích rõ ràng (Explainable Signals) để phục vụ điều tra và phân tích trên Dashboard. Hệ thống kết hợp hai phương pháp: **Rule-based Detection (Hệ thống luật nghiệp vụ)** và **Machine Learning Baseline (Mô hình học máy cơ sở)**.

---

## 6.1. Phát hiện Gian lận dựa trên Tập Luật (Rule-based Detection)

Dựa trên các kết quả định lượng từ bước EDA trên bộ dữ liệu **Sparkov**, bộ quy tắc khởi tạo gồm **6 luật nghiệp vụ (R001 – R006)** có khả năng giải thích trực tiếp cho Fraud Analyst:

| Mã luật | Tên quy tắc | Tín hiệu & Điều kiện Kích hoạt Mẫu (Calibrated từ Sparkov EDA) | Trọng số gợi ý ($w_i$) | Ý nghĩa Nghiệp vụ |
| :--- | :--- | :--- | :--- | :--- |
| **R001** | **High Amount vs Card History** | `amt_to_card_mean_ratio >= 5.0` và `amt >= 300.0` USD | `0.25` | Giao dịch có số tiền cao đột biến so với thói quen chi tiêu lịch sử của chính thẻ `cc_num` đó. |
| **R002** | **Rapid Card Velocity Burst** | `tx_count_1h >= 4` hoặc `tx_count_6h >= 8` hoặc `amt_sum_24h >= 1500.0` USD | `0.25` | Tần suất quẹt thẻ hoặc tổng tiền lũy kế tăng vọt trong thời gian ngắn (*Fraud Burst* khi thẻ bị lộ). |
| **R003** | **High Merchant Diversity** | `unique_merchants_24h >= 6` và `time_since_last_tx_sec <= 600` (10 phút) | `0.15` | Thẻ quẹt liên tiếp tại nhiều cửa hàng khác nhau trong khoảng thời gian cực ngắn. |
| **R004** | **Category Anomaly & Card Testing** | (`category IN ('shopping_net', 'misc_net')` và `amt_to_cat_median_ratio >= 20.0`) **HOẶC** (`category IN ('gas_transport', 'grocery_net')` và `amt <= 15.0` kèm `tx_count_1h >= 2`) | `0.20` | Bắt đồng thời 2 kịch bản trong Sparkov: quẹt giá trị lớn ở kênh mua sắm trực tuyến (`_net`) hoặc quẹt thử thẻ mệnh giá nhỏ (*Card Testing*) ở trạm xăng/tạp hóa trước khi rút lớn. |
| **R005** | **Impossible Travel Velocity** | `merch_to_merch_dist_km >= 50.0` và `implied_speed_kmh >= 250.0` km/h | `0.25` | Hai lần quẹt thẻ liên tiếp diễn ra tại hai tọa độ cửa hàng cách xa nhau với vận tốc di chuyển vượt quá khả năng di chuyển đường bộ thông thường. |
| **R006** | **High-Risk Night Window** | `is_night_tx == TRUE` (`22:00–03:59`) và `amt >= 250.0` USD | `0.15` | Giao dịch giá trị lớn phát sinh vào khung giờ đêm khuya khi chủ thẻ thường đang nghỉ ngơi (khung giờ có tỷ lệ gian lận cao gấp 5–6 lần ban ngày). |

> **Nguyên tắc tinh chỉnh ngưỡng (Rule Calibration):**
> - Một giao dịch có số tiền lớn đơn lẻ không đồng nghĩa chắc chắn là gian lận.
> - Ngưỡng của từng luật (`R001`–`R006`) được cấu hình hóa trong `configs/config.yaml` và được tinh chỉnh dựa trên tập **Out-of-Time Validation** nhằm cân bằng giữa tỷ lệ bắt trúng gian lận (Recall) và khối lượng cảnh báo mà Fraud Analyst phải duyệt mỗi ngày (Alert Review Workload).

---

## 6.2. Cơ chế Chấm điểm Rủi ro & Phân tầng Cảnh báo (Risk Scoring & Bands)

### 1. Điểm Rủi ro theo Luật (`Rule Risk Score`)

Điểm rủi ro từ hệ thống luật được tính bằng tổng có trọng số của các quy tắc bị kích hoạt và chuẩn hóa về đoạn $[0.0, 1.0]$:

$$\text{RiskScore}_{\text{rule}} = \min\left(1.0, \sum_{i=1}^{6} w_i \cdot r_i\right)$$

Trong đó:
- $r_i \in \{0, 1\}$ là trạng thái kích hoạt của luật thứ $i$ (`1` nếu vi phạm, `0` nếu bình thường).
- $w_i > 0$ là trọng số rủi ro của luật thứ $i$.

### 2. Điểm Rủi ro Kết hợp (`Hybrid Risk Score` — Tùy chọn khi chạy song song Rules + ML)

Khi cả Rule Engine và mô hình ML Baseline cùng hoạt động, hệ thống lưu riêng từng bản ghi trong `core.fraud_predictions` (`detection_method = 'RULE_BASED'` hoặc `'ML_MODEL'`) hoặc kết hợp theo công thức:

$$\text{RiskScore}_{\text{hybrid}} = \alpha \cdot P_{\text{ML}}(\text{fraud} \mid x) + (1 - \alpha) \cdot \text{RiskScore}_{\text{rule}}, \quad \alpha \in [0, 1]$$

### 3. Phân tầng Mức độ Rủi ro (`Risk Level Bands`)

| Khoảng điểm (`risk_score`) | Mức độ rủi ro (`risk_level`) | Trạng thái gắn cờ (`is_flagged`) | Hành động trên Hệ thống & Dashboard |
| :--- | :--- | :--- | :--- |
| **`0.00` – `0.29`** | `LOW` | `FALSE` | Giao dịch bình thường; ghi nhận vào kho phân tích lịch sử, không sinh cảnh báo. |
| **`0.30` – `0.69`** | `MEDIUM` | `TRUE` | Giao dịch đáng ngờ mức trung bình; sinh bản ghi trong `core.fraud_alerts` với trạng thái `NEW` để rà soát theo lô. |
| **`0.70` – `1.00`** | `HIGH` | `TRUE` | Giao dịch rủi ro cao; sinh cảnh báo ưu tiên cao trên trang *Live Monitoring* và đẩy qua SSE/WebSocket tức thời. |

### 4. Cấu trúc Giải thích Cảnh báo (`alert_reason` JSONB)

Mỗi cảnh báo trong bảng `core.fraud_alerts` lưu trữ đầy đủ bằng chứng giải thích dưới dạng JSONB để hiển thị trên trang **Transaction Investigation**:

```json
{
  "detection_method": "RULE_BASED",
  "risk_score": 0.70,
  "risk_level": "HIGH",
  "triggered_rules": [
    {
      "rule_id": "R001",
      "rule_name": "High Amount vs Card History",
      "weight": 0.25,
      "observed_value": 14.8,
      "threshold": 5.0,
      "description": "Transaction amount ($985.50) is 14.8x higher than card historical average ($66.50)."
    },
    {
      "rule_id": "R005",
      "rule_name": "Impossible Travel Velocity",
      "weight": 0.25,
      "observed_value": 412.5,
      "threshold": 250.0,
      "description": "Consecutive swipe occurred 82.5 km away within 12 minutes (implied speed: 412.5 km/h)."
    },
    {
      "rule_id": "R004",
      "rule_name": "Category Anomaly (Online Shopping)",
      "weight": 0.20,
      "observed_value": 118.7,
      "threshold": 20.0,
      "description": "Amount in 'shopping_net' is 118.7x the category median ($8.30)."
    }
  ]
}
```

---

## 6.3. Mô hình Học máy Cơ sở & Quy trình Đánh giá (ML Baseline & Evaluation)

### 1. Lựa chọn Mô hình Cơ sở (ML Baseline)

Dự án triển khai mô hình phân loại có giám sát gọn nhẹ, minh bạch và hiệu quả trên dữ liệu bảng:
- **Baseline 1 (Tuyến tính & Giải thích dễ dàng):** `LogisticRegression(class_weight="balanced")` đi kèm `StandardScaler` và `OneHotEncoder` / `FrequencyEncoder`.
- **Baseline 2 (Cây quyết định xử lý phi tuyến):** `RandomForestClassifier(class_weight="balanced_subsample")` hoặc `LightGBM` (`scale_pos_weight` tính từ tỷ lệ mất cân bằng `~172:1` trên tập Train).

### 2. Quy tắc Huấn luyện Chống Rò rỉ Dữ liệu (Zero-Leakage Training Protocol)

1. **Chia tập theo thời gian (Chronological Split):**
   - **Train Set:** `85%` đầu của `fraudTrain.csv` theo thứ tự thời gian (`2019-01-01` $\rightarrow$ `2020-03-31`).
   - **Validation Set:** `15%` cuối của `fraudTrain.csv` (`2020-04-01` $\rightarrow$ `2020-06-21`) — dùng để chọn ngưỡng phân loại tối ưu ($\tau^*$) và tinh chỉnh siêu tham số.
   - **Test Set:** Toàn bộ `fraudTest.csv` (`2020-06-21` $\rightarrow$ `2020-12-31`) — chỉ chạy đánh giá một lần để báo cáo kết quả cuối cùng.
2. **Không đưa ID tĩnh vào mô hình:** Loại bỏ hoàn toàn `trans_num`, `cc_num`, `first`, `last`, `street` khỏi ma trận đặc trưng `X`.
3. **Fit Preprocessing độc lập trên Train:** Các bộ chuẩn hóa số học (`StandardScaler`), mã hóa phân loại (`OneHotEncoder`/`FrequencyEncoder`) và bảng tra cứu trung vị theo danh mục (`category_median_amt`) chỉ được phép `fit` trên **Train Set**.

### 3. Bộ Độ đo Đánh giá Chuẩn (`src/fraud_detection/evaluation/metrics.py`)

Do tỷ lệ gian lận chỉ chiếm `0.579%` (Train) và `0.386%` (Test), một mô hình dự đoán tất cả là hợp lệ vẫn đạt `99.61% Accuracy`. Do đó, hệ thống **không sử dụng Accuracy**, mà đánh giá toàn diện bằng:

| Độ đo (Metric) | Công thức / Ý nghĩa | Mục tiêu trong bài toán Gian lận |
| :--- | :--- | :--- |
| **PR-AUC (Average Precision)** | Diện tích dưới đường cong Precision–Recall | **Độ đo quan trọng nhất** phản ánh chất lượng xếp hạng rủi ro trên dữ liệu mất cân bằng cực đại. |
| **Precision** | $\frac{TP}{TP + FP}$ | Tỷ lệ cảnh báo đúng trên tổng số cảnh báo phát ra (giúp kiểm soát tỷ lệ báo động giả `False Positive`). |
| **Recall (Sensitivity)** | $\frac{TP}{TP + FN}$ | Tỷ lệ giao dịch gian lận thực tế bị hệ thống bắt giữ thành công. |
| **F1-Score** | $\frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$ | Trung bình điều hòa giữa Precision và Recall tại ngưỡng quyết định $\tau$. |
| **Confusion Matrix** | Ma trận $[TN, FP; FN, TP]$ | Định lượng cụ thể số ca bắt đúng ($TP$), bỏ lọt ($FN$) và báo nhầm ($FP$). |
| **Value Recall (Financial Recall)** | $\frac{\sum \text{amt}_{TP}}{\sum \text{amt}_{TP + FN}}$ | Tỷ lệ **tổng số tiền gian lận (USD)** được phát hiện kịp thời trên tổng giá trị thiệt hại thực tế. |
