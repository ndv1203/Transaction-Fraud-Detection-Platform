# 03. Chiến lược Dữ liệu & Từ điển Dữ liệu (Dataset Strategy & Data Dictionary)

Tài liệu này quy định chi tiết bộ dữ liệu chuẩn của dự án, vai trò của từng nguồn dữ liệu, quy tắc chuẩn hóa schema các trường gốc và danh mục đặc trưng (Feature Catalog) phục vụ phát hiện gian lận.

---

## 3.1. Bộ dữ liệu Chuẩn: Sparkov Credit Card Fraud Detection

Dự án thống nhất sử dụng bộ dữ liệu **Sparkov Credit Card Fraud Detection** (gồm hai tập `fraudTrain.csv` và `fraudTest.csv` được sinh từ trình mô phỏng giao dịch thẻ tín dụng Sparkov).

### Lý do lựa chọn bộ dữ liệu Sparkov

- **Có dấu thời gian thực tế (`trans_date_trans_time` & `unix_time`):** Khác với các bộ dữ liệu ẩn danh (như PCA V1–V28) hoặc chỉ có bước thời gian giả định, Sparkov cung cấp thời gian chính xác đến từng giây xuyên suốt 2 năm (`2019–2020`), cho phép thiết kế các cửa sổ trượt (`1h`, `6h`, `24h`) và chia tập theo thời gian thực (Out-of-Time Split).
- **Giàu ngữ cảnh thực thể:** Có định danh thẻ (`cc_num`), cửa hàng (`merchant`), danh mục chi tiêu (`category`), tọa độ địa lý của cả chủ thẻ (`lat`, `long`) lẫn điểm quẹt thẻ (`merch_lat`, `merch_long`), và thông tin nhân khẩu học (`dob`, `gender`, `job`, `city_pop`).
- **Quy mô đủ lớn để kiểm chứng kỹ thuật Data Engineering:** Tổng cộng **1,852,394 bản ghi** (`1,296,675` dòng ở `fraudTrain.csv` và `555,719` dòng ở `fraudTest.csv`).

### Thống kê Tổng quan Bộ dữ liệu (Dataset Assessment Summary)

| Tiêu chí đánh giá | Tập Huấn luyện (`fraudTrain.csv`) | Tập Kiểm thử (`fraudTest.csv`) | Ý nghĩa kỹ thuật |
| :--- | :--- | :--- | :--- |
| **Khoảng thời gian** | `2019-01-01` $\rightarrow$ `2020-06-21` | `2020-06-21` $\rightarrow$ `2020-12-31` | Không chồng lấn thời gian; phù hợp đánh giá Out-of-Time. |
| **Số lượng bản ghi** | `1,296,675` giao dịch | `555,719` giao dịch | Đủ lớn để kiểm thử Batch ETL, Parquet & PostgreSQL indexing. |
| **Số cột gốc** | `23` cột (kể cả cột chỉ số `Unnamed: 0`) | `23` cột (kể cả cột chỉ số `Unnamed: 0`) | Giữ lại `18` cột cốt lõi sau bước `cleaner.py`. |
| **Tỷ lệ gian lận (`is_fraud = 1`)** | `7,506` giao dịch (**`0.579%`**) | `2,145` giao dịch (**`0.386%`**) | Mất cân bằng nghiêm trọng (~172:1 trên Train) và có hiện tượng Concept Drift nhẹ. |
| **Số lượng thẻ (`cc_num`)** | `983` thẻ duy nhất | `924` thẻ duy nhất (có **16 thẻ mới** chưa từng xuất hiện ở Train) | Cần xử lý bài toán *Cold-Start* và không đưa trực tiếp `cc_num` vào model. |
| **Số lượng cửa hàng (`merchant`)** | `693` cửa hàng | `693` cửa hàng (`0` cửa hàng mới) | Tập cửa hàng ổn định giữa Train và Test. |
| **Giá trị khuyết (Missing Values)** | `0%` trên tập gốc | `0%` trên tập gốc | Vẫn phải cài đặt tầng kiểm định Pandera để bắt lỗi cho luồng Streaming / Batch mới. |

---

## 3.2. Vai trò Dữ liệu & Chống Rò rỉ (Data Roles & Leakage Prevention)

| Nguồn dữ liệu | Nguồn phát sinh (Source) | Mục đích sử dụng trong Nền tảng |
| :--- | :--- | :--- |
| **Dữ liệu lịch sử (Historical Transactions)** | `fraudTrain.csv` & `fraudTest.csv` | Chạy Batch ETL, phân tích EDA, xây dựng kho dữ liệu lịch sử và huấn luyện mô hình. |
| **Dữ liệu luồng (Incoming Transactions)** | `scripts/simulate_transactions.py` (phát lại các sự kiện từ tập Test theo thời gian thực qua Kafka) | Kiểm thử đường ống giám sát cận thời gian thực (Near Real-time Monitoring). |
| **Nhãn thực tế (Ground-truth Labels)** | Cột `is_fraud` (`0` hoặc `1`) | **Chỉ dùng để đánh giá ngoại tuyến (Offline Evaluation)** hoặc đối soát sau khi điều tra (Label Reconciliation). |

> **Quy tắc Bắt buộc Chống Rò rỉ Dữ liệu (Strict Leakage Prevention):**
> 1. **Tuyệt đối không dùng `is_fraud` làm đầu vào** cho bất kỳ quy tắc (Rule) hay phép tính đặc trưng (Feature) nào tại thời điểm giao dịch vừa phát sinh.
> 2. Trong cơ sở dữ liệu PostgreSQL, nhãn thực tế phải được tách riêng sang bảng `core.transaction_labels`, độc lập hoàn toàn với bảng `core.transactions`, `core.transaction_features` và `core.fraud_predictions`.
> 3. Khi tính các đặc trưng lịch sử theo thẻ (`tx_count_1h`, `amt_sum_24h`, `amt_to_card_mean_ratio`), chỉ được phép tổng hợp từ **các giao dịch có `event_time` nhỏ hơn hoặc bằng thời điểm hiện tại** (`past-only rolling window`), không bao giờ nhìn thấy giao dịch tương lai.

---

## 3.3. Từ điển 22 Trường Dữ liệu Gốc & Quy tắc Chuẩn hóa Tên cột

Ngay tại bước `preprocessing/cleaner.py`, hệ thống thực hiện **2 thao tác chuẩn hóa bắt buộc** để đồng bộ xuyên suốt từ `DataFrame` $\rightarrow$ `Parquet` $\rightarrow$ `PostgreSQL` $\rightarrow$ `FastAPI` $\rightarrow$ `React Dashboard`:

1. **Đổi tên 3 cột trùng từ khóa SQL / thiếu đồng nhất:**
   - `state` $\rightarrow$ **`state_code`** (tránh trùng từ khóa `STATE` trong SQL)
   - `long` $\rightarrow$ **`lon`** (tránh trùng kiểu dữ liệu `LONG` trong SQL)
   - `merch_long` $\rightarrow$ **`merch_lon`** (đồng bộ quy ước đặt tên với `lon`)
2. **Loại bỏ 4 cột nhiễu / định danh cá nhân (PII) khi đưa vào pipeline phân tích & mô hình:**
   - Loại bỏ `Unnamed: 0` (chỉ số dòng vô nghĩa của CSV), `first`, `last`, `street` (thông tin PII định danh tĩnh dễ gây học vẹt / overfitting).

| STT | Tên cột gốc (CSV) | Tên cột chuẩn hóa | Kiểu dữ liệu (Pandas / SQL) | Ý nghĩa chi tiết | Vai trò trong Pipeline |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | `Unnamed: 0` | *(Loại bỏ)* | `int64` | Chỉ số dòng tự sinh trong file CSV gốc | Bỏ ngay khi đọc CSV (`cleaner.py`) |
| 1 | `trans_date_trans_time` | `trans_date_trans_time` | `datetime64[ns]` / `TIMESTAMPTZ` | Thời điểm phát sinh giao dịch (`YYYY-MM-DD HH:MM:SS`) | Mốc thời gian sự kiện (`event_time`), dùng chia tập và tính đặc trưng thời gian |
| 2 | `cc_num` | `cc_num` | `string` / `VARCHAR(32)` | Mã số thẻ tín dụng của khách hàng | **Khóa nhóm (Group Key)** để tính lịch sử quẹt thẻ (`1h`, `6h`, `24h`); không đưa trực tiếp vào ML |
| 3 | `merchant` | `merchant` | `category` / `VARCHAR(255)` | Tên đơn vị chấp nhận thẻ / cửa hàng | Thực thể cửa hàng (`core.merchants`), dùng tính Frequency / Risk Encoding |
| 4 | `category` | `category` | `category` / `VARCHAR(64)` | Danh mục chi tiêu (14 nhóm: `shopping_net`, `grocery_pos`, `gas_transport`...) | Đặc trưng phân loại cốt lõi và chiều phân tích trên Dashboard |
| 5 | `amt` | `amt` | `float32` / `NUMERIC(18,2)` | Số tiền giao dịch (đơn vị USD) | Đặc trưng số quan trọng nhất; lưu kiểu `NUMERIC(18,2)` trong PostgreSQL |
| 6 | `first` | *(Loại bỏ khi train)* | `string` | Tên của chủ thẻ | Lưu trong payload `raw`, loại bỏ khỏi `core` & ML để tránh học vẹt |
| 7 | `last` | *(Loại bỏ khi train)* | `string` | Họ của chủ thẻ | Lưu trong payload `raw`, loại bỏ khỏi `core` & ML để tránh học vẹt |
| 8 | `gender` | `gender` | `category` / `VARCHAR(8)` | Giới tính chủ thẻ (`M` hoặc `F`) | Thuộc tính nhân khẩu học của thẻ (`core.cards`) |
| 9 | `street` | *(Loại bỏ khi train)* | `string` | Địa chỉ đường phố của chủ thẻ | Lưu trong payload `raw`, loại bỏ khi đưa vào mô hình |
| 10 | `city` | `city` | `string` / `VARCHAR(128)` | Thành phố cư trú của chủ thẻ | Dùng hiển thị điều tra giao dịch và phân tích theo khu vực |
| 11 | `state` | **`state_code`** | `category` / `VARCHAR(16)` | Mã bang của chủ thẻ (2 ký tự, VD: `NY`, `CA`, `TX`) | Đổi tên từ `state`; dùng làm đặc trưng vùng địa lý và bộ lọc Dashboard |
| 12 | `zip` | `zip` | `string` / `VARCHAR(16)` | Mã bưu chính nơi cư trú của chủ thẻ | Thuộc tính địa lý gắn với hồ sơ thẻ |
| 13 | `lat` | `lat` | `float32` / `NUMERIC(9,6)` | Vĩ độ nơi cư trú của chủ thẻ | Dùng tính khoảng cách Haversine tới cửa hàng |
| 14 | `long` | **`lon`** | `float32` / `NUMERIC(9,6)` | Kinh độ nơi cư trú của chủ thẻ | Đổi tên từ `long`; dùng tính khoảng cách Haversine tới cửa hàng |
| 15 | `city_pop` | `city_pop` | `int32` / `INTEGER` | Quy mô dân số thành phố của chủ thẻ | Đặc trưng số phản ánh mật độ đô thị |
| 16 | `job` | `job` | `category` / `VARCHAR(128)` | Nghề nghiệp của chủ thẻ (~494 nghề) | Thuộc tính nhân khẩu học (xử lý bằng Frequency Encoding) |
| 17 | `dob` | `dob` | `datetime64[ns]` / `DATE` | Ngày tháng năm sinh của chủ thẻ (`YYYY-MM-DD`) | Dùng tính tuổi chủ thẻ (`customer_age`) tại thời điểm giao dịch |
| 18 | `trans_num` | `trans_num` | `string` / `VARCHAR(64)` | Mã định danh duy nhất của giao dịch (chuỗi hex 32 ký tự) | **Khóa nghiệp vụ duy nhất (Unique Business Key)** để chống trùng lặp (Idempotency) |
| 19 | `unix_time` | `unix_time` | `int64` / `BIGINT` | Thời gian giao dịch tính bằng giây (Unix Epoch) | Sắp xếp thứ tự sự kiện và tính độ trễ giữa 2 lần quẹt thẻ liên tiếp |
| 20 | `merch_lat` | `merch_lat` | `float32` / `NUMERIC(9,6)` | Vĩ độ của cửa hàng thực hiện giao dịch | Dùng tính khoảng cách chủ thẻ–cửa hàng và khoảng cách giữa 2 cửa hàng liên tiếp |
| 21 | `merch_long` | **`merch_lon`** | `float32` / `NUMERIC(9,6)` | Kinh độ của cửa hàng thực hiện giao dịch | Đổi tên từ `merch_long`; dùng tính khoảng cách địa lý và tốc độ di chuyển |
| 22 | `is_fraud` | `is_fraud` | `int8` / `BOOLEAN` | Nhãn thực tế: `1` (`TRUE`) = Gian lận, `0` (`FALSE`) = Hợp lệ | Tách riêng vào `core.transaction_labels` phục vụ đánh giá và đối soát |

---

## 3.4. Danh mục Đặc trưng Kỹ thuật (Engineered Feature Catalog)

Toàn bộ các đặc trưng trong `preprocessing/feature_engineering.py` và bảng `core.transaction_features` được thiết kế dựa trên bằng chứng thực nghiệm từ EDA, tuân thủ nghiêm ngặt nguyên tắc **chỉ sử dụng thông tin quá khứ và hiện tại (Zero Future Leakage)**:

| Nhóm đặc trưng | Tên đặc trưng (Feature Name) | Kiểu dữ liệu | Công thức & Định nghĩa Nghiệp vụ | Xử lý giá trị đầu tiên / Null |
| :--- | :--- | :--- | :--- | :--- |
| **1. Số tiền & Tương tác Danh mục** | `log_amt` | `NUMERIC(12,6)` | $\ln(1 + \text{amt})$ giúp giảm độ lệch phải (right-skewness) của số tiền giao dịch. | Luôn xác định vì $\text{amt} > 0$. |
| | `amt_to_card_mean_ratio` | `NUMERIC(12,4)` | Tỷ lệ giữa `amt` hiện tại và trung bình số tiền lịch sử trước đó của cùng `cc_num`. | Gán bằng `1.0` nếu là giao dịch đầu tiên của thẻ. |
| | `amt_to_cat_median_ratio` | `NUMERIC(12,4)` | Tỷ lệ giữa `amt` hiện tại và mức trung vị lịch sử của danh mục `category` tương ứng (bắt hành vi quẹt lớn ở `shopping_net` hoặc quẹt thử mệnh giá nhỏ ở `gas_transport`). | Tra cứu từ bảng thống kê tập Train; fallback về trung vị toàn cục nếu thiếu. |
| **2. Tần suất & Lịch sử theo Thẻ (Card Velocity)** | `tx_count_1h` | `INTEGER` | Số lượng giao dịch của cùng thẻ `cc_num` trong vòng **1 giờ** trước đó. | `1` (nếu tính cả giao dịch hiện tại) hoặc `0` (nếu chỉ tính giao dịch trước đó — thống nhất quy ước trong code). |
| | `tx_count_6h` | `INTEGER` | Số lượng giao dịch của cùng thẻ `cc_num` trong vòng **6 giờ** trước đó (bắt chùm gian lận *Fraud Burst*). | Tương tự `tx_count_1h`. |
| | `tx_count_24h` | `INTEGER` | Số lượng giao dịch của cùng thẻ `cc_num` trong vòng **24 giờ** trước đó. | Tương tự `tx_count_1h`. |
| | `amt_sum_1h` | `NUMERIC(18,2)` | Tổng số tiền đã quẹt của cùng thẻ `cc_num` trong **1 giờ** qua. | Khởi tạo bằng `amt` hiện tại (hoặc `0.00`). |
| | `amt_sum_24h` | `NUMERIC(18,2)` | Tổng số tiền đã quẹt của cùng thẻ `cc_num` trong **24 giờ** qua. | Khởi tạo bằng `amt` hiện tại (hoặc `0.00`). |
| | `unique_merchants_24h` | `INTEGER` | Số lượng cửa hàng (`merchant`) phân biệt mà thẻ `cc_num` đã giao dịch trong **24 giờ** qua. | Khởi tạo bằng `1`. |
| | `time_since_last_tx_sec` | `BIGINT` | Khoảng thời gian (giây) kể từ lần quẹt thẻ liền trước của cùng `cc_num` ($\Delta t = \text{unix\_time}_t - \text{unix\_time}_{t-1}$). | Điền giá trị mặc định lớn (VD: `86400` giây = 24h) kèm cờ `is_first_tx = 1`. |
| **3. Địa lý & Di chuyển (Geospatial & Velocity)** | `dist_home_to_merch_km` | `NUMERIC(10,3)` | Khoảng cách đường chim bay Haversine (km) từ địa chỉ chủ thẻ (`lat`, `lon`) tới cửa hàng (`merch_lat`, `merch_lon`). | Tính trực tiếp từ 4 tọa độ của bản ghi hiện tại. |
| | `merch_to_merch_dist_km` | `NUMERIC(10,3)` | Khoảng cách Haversine (km) giữa cửa hàng của giao dịch liền trước và cửa hàng hiện tại trên cùng thẻ `cc_num`. | Gán bằng `0.0` cho giao dịch đầu tiên của thẻ. |
| | `implied_speed_kmh` | `NUMERIC(10,2)` | Vận tốc di chuyển ngầm định giữa 2 lần quẹt thẻ liên tiếp: $\frac{\text{merch\_to\_merch\_dist\_km}}{\max(\Delta t / 3600, 0.05)}$ (chặn dưới $0.05\text{h} = 3\text{ phút}$ để tránh chia cho 0). Phát hiện hiện tượng *Impossible Travel*. | Gán bằng `0.0` cho giao dịch đầu tiên của thẻ. |
| **4. Thời gian & Nhân khẩu học** | `hour_of_day` | `SMALLINT` | Giờ thực hiện giao dịch trong ngày (`0` đến `23`). | Trích xuất trực tiếp từ `trans_date_trans_time`. |
| | `day_of_week` | `SMALLINT` | Thứ trong tuần (`0` = Thứ Hai $\rightarrow$ `6` = Chủ Nhật). | Trích xuất trực tiếp từ `trans_date_trans_time`. |
| | `is_weekend` | `BOOLEAN` | Cờ đánh dấu giao dịch vào Thứ Bảy hoặc Chủ Nhật (`day_of_week >= 5`). | `TRUE` / `FALSE`. |
| | `is_night_tx` | `BOOLEAN` | Cờ đánh dấu giao dịch nằm trong **khung giờ rủi ro cao ban đêm (`22:00` $\rightarrow$ `03:59`)** (nơi tỷ lệ gian lận tăng vọt trong EDA). | `TRUE` / `FALSE`. |
| | `customer_age` | `NUMERIC(5,2)` | Tuổi của chủ thẻ tại thời điểm giao dịch: $(\text{trans\_date\_trans\_time} - \text{dob}) / 365.25$. | Tính trực tiếp từ `trans_date_trans_time` và `dob`. |
