# Từ điển Dữ liệu (Data Dictionary) — Sparkov Credit Card Fraud

Bộ dữ liệu sử dụng chính cho dự án là **Sparkov Credit Card Fraud Detection** (gồm `fraudTrain.csv` và `fraudTest.csv`).

---

## 1. Các trường dữ liệu gốc & Chuẩn hóa tên cột (22 cột)

Ngay tại bước `preprocessing/cleaner.py`, một số cột gốc trùng với từ khóa SQL sẽ được chuẩn hóa tên để đồng bộ xuyên suốt từ DataFrame $\rightarrow$ Model $\rightarrow$ Database $\rightarrow$ API/UI:
- `state` $\rightarrow$ **`state_code`**
- `long` $\rightarrow$ **`lon`**
- `merch_long` $\rightarrow$ **`merch_lon`**

| Tên cột gốc (CSV) | Tên cột chuẩn hóa | Kiểu dữ liệu | Ý nghĩa | Vai trò trong Pipeline |
| :--- | :--- | :--- | :--- | :--- |
| `Unnamed: 0` | *(Loại bỏ)* | `int64` | Chỉ số dòng gốc trong file CSV | Loại bỏ ở bước `cleaner.py` |
| `trans_date_trans_time` | `trans_date_trans_time` | `datetime` | Thời điểm phát sinh giao dịch (`YYYY-MM-DD HH:MM:SS`) | Chia tập theo thời gian & tạo đặc trưng thời gian |
| `cc_num` | `cc_num` | `int64` / `str` | Mã số thẻ tín dụng của khách hàng | Khóa nhóm (Group Key) để tính lịch sử giao dịch theo thẻ |
| `merchant` | `merchant` | `string` | Tên cửa hàng / đơn vị chấp nhận thẻ | Phân loại / Frequency hoặc Target Encoding |
| `category` | `category` | `string` | Danh mục chi tiêu (VD: `grocery_pos`, `shopping_net`...) | Đặc trưng phân loại quan trọng |
| `amt` | `amt` | `float32` | Số tiền giao dịch (USD) | Đặc trưng số cốt lõi |
| `first` | *(Loại bỏ khi train)* | `string` | Tên chủ thẻ | Bỏ khi đưa vào Model |
| `last` | *(Loại bỏ khi train)* | `string` | Họ chủ thẻ | Bỏ khi đưa vào Model |
| `gender` | `gender` | `string` | Giới tính chủ thẻ (`M` / `F`) | Đặc trưng phân loại |
| `street` | *(Loại bỏ khi train)* | `string` | Địa chỉ đường phố của chủ thẻ | Bỏ khi đưa vào Model |
| `city` | `city` | `string` | Thành phố của chủ thẻ | Dùng hiển thị hoặc gộp vùng địa lý |
| `state` | **`state_code`** | `string` | Mã bang của chủ thẻ (viết tắt 2 ký tự) | Đặc trưng phân loại (đổi tên tránh trùng keyword `STATE`) |
| `zip` | `zip` | `int32` / `str` | Mã bưu chính của chủ thẻ | Định danh vùng địa lý |
| `lat` | `lat` | `float32` | Vĩ độ nơi cư trú của chủ thẻ | Dùng tính khoảng cách địa lý tới cửa hàng |
| `long` | **`lon`** | `float32` | Kinh độ nơi cư trú của chủ thẻ | Dùng tính khoảng cách địa lý (đổi tên tránh trùng keyword `LONG`) |
| `city_pop` | `city_pop` | `int32` | Dân số thành phố của chủ thẻ | Đặc trưng số |
| `job` | `job` | `string` | Nghề nghiệp của chủ thẻ | Đặc trưng phân loại (nhiều giá trị) |
| `dob` | `dob` | `date` | Ngày sinh của chủ thẻ (`YYYY-MM-DD`) | Dùng tính tuổi (`customer_age`) tại thời điểm giao dịch |
| `trans_num` | `trans_num` | `string` | Mã định danh duy nhất của giao dịch (32 ký tự hex) | Khóa chính (Primary Key) trong Database |
| `unix_time` | `unix_time` | `int64` | Thời gian giao dịch dạng Unix timestamp (giây) | Tính khoảng cách thời gian giữa 2 lần quẹt thẻ |
| `merch_lat` | `merch_lat` | `float32` | Vĩ độ của cửa hàng (`merchant`) | Dùng tính khoảng cách địa lý |
| `merch_long` | **`merch_lon`** | `float32` | Kinh độ của cửa hàng (`merchant`) | Dùng tính khoảng cách địa lý (đổi tên cho đồng bộ với `lon`) |
| `is_fraud` | `is_fraud` | `int8` (`0`/`1`) | **Nhãn mục tiêu**: `1` = Gian lận, `0` = Hợp lệ | Target (`y`) |

---

## 2. Các nhóm Đặc trưng dự kiến trích xuất (`preprocessing/feature_engineering.py`)

1. **Đặc trưng Thời gian (Temporal Features)**:
   - `hour_of_day`, `day_of_week`, `is_weekend`, `is_night_tx` (giao dịch lúc nửa đêm/rạng sáng thường có rủi ro cao).
2. **Đặc trưng Địa lý (Geospatial Features)**:
   - `distance_to_merchant_km`: Khoảng cách Haversine giữa tọa độ chủ thẻ (`lat`, `lon`) và cửa hàng (`merch_lat`, `merch_lon`).
3. **Đặc trưng Tần suất & Lịch sử theo Thẻ (`cc_num` Velocity & Aggregations)**:
   - `time_since_last_tx`: Số giây kể từ lần quẹt thẻ gần nhất của cùng `cc_num`.
   - `tx_count_1h`, `tx_count_24h`: Số lượng giao dịch của thẻ đó trong 1 giờ / 24 giờ gần nhất.
   - `amt_sum_24h`, `amt_vs_card_avg`: Tổng chi tiêu trong 24h và tỷ lệ số tiền giao dịch hiện tại so với mức trung bình lịch sử của thẻ đó.
4. **Đặc trưng Nhân khẩu học (Demographic Features)**:
   - `customer_age`: Tuổi chủ thẻ tính từ `dob` và `trans_date_trans_time`.
