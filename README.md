# Hệ thống Dự đoán Khả năng Trúng tuyển Đại học tại Việt Nam
## Module Thu thập, Chuẩn hóa & Nạp Dữ liệu Google Trends (Social Interest Signal Engine)

Hệ thống thu thập tự động, chuẩn hóa tỷ lệ chéo (**Anchor Normalization**) và lưu trữ dữ liệu từ **Google Trends** vào **Data Lake** và **Data Warehouse DuckDB** cho bài toán dự đoán xác suất trúng tuyển Đại học dựa trên dữ liệu công khai bên ngoài nhà trường:

> **"An Institution-Independent Framework for Predicting University Admission Chances in Vietnam: Integrating Public Cut-off Scores, Exam Score Distributions, and Labor Market Signals"**

---

## 1. Vai trò của Dữ liệu Google Trends trong Hệ thống

* **Biến đầu vào**: Tín hiệu thị trường & Mức độ quan tâm của xã hội (**Social Interest Signals**).
* **Dữ liệu đại diện**: Chỉ số tìm kiếm Google Trends theo chuỗi thời gian (Weekly / Daily) và phân bố địa lý theo 63 tỉnh/thành phố tại Việt Nam.
* **Ý nghĩa nghiệp vụ**: Sức hút và mức độ quan tâm của xã hội đối với một ngành học/trường đại học có mối tương quan trực tiếp với mức độ cạnh tranh hồ sơ tuyển sinh và xu hướng biến động điểm chuẩn hàng năm.

---

## 2. Kiến trúc & Kỹ thuật Xử lý Dữ liệu Cốt lõi

```text
IS405.R11-Big-Data/
├── config/
│   ├── keywords_it.yaml         # Cấu hình danh mục từ khóa ngành, trường, tín hiệu tuyển sinh & việc làm
│   └── scraper_config.yaml      # Cấu hình timeframe (5y, 1y, 3m), rate limit, storage
├── src/
│   ├── scraper/
│   │   ├── trends_client.py     # Client bọc pytrends chống lỗi urllib3, rate limit 429 & auto-retry
│   │   ├── normalizer.py        # Thuật toán Anchor Keyword Normalization liên batch
│   │   └── google_trends_scraper.py # Pipeline điều phối thu thập & xử lý
│   ├── storage/
│   │   └── lake_manager.py      # Quản lý Data Lake (Parquet/CSV) & Data Warehouse (DuckDB)
│   └── utils/
│       └── logger.py            # Logging chuẩn định dạng UTF-8
├── data/
│   ├── lake/
│   │   ├── raw/                 # Vùng lưu trữ thô theo từng batch
│   │   │   ├── interest_over_time/
│   │   │   ├── interest_by_region/
│   │   │   └── checkpoints/     # Trạng thái cào tránh trùng lặp
│   │   └── normalized/          # Bảng Master đã chuẩn hóa thang đo toàn cục
│   └── warehouse/
│       └── trends.duckdb        # Data Warehouse DuckDB phục vụ phân tích SQL
├── notebooks/
│   └── 01_google_trends_analysis.ipynb # Notebook EDA, trực quan hóa và kiểm định dữ liệu
├── run_scraper.py               # CLI điều phối hệ thống một chạm
├── view_duckdb.py               # Công cụ CLI tương tác xem dữ liệu DuckDB
└── requirements.txt             # Danh sách thư viện phụ thuộc
```

### Các Điểm Sáng Kỹ Thuật:
1. **Chuẩn hóa Thang đo (Anchor Keyword Normalization)**:
   * Google Trends giới hạn tối đa 5 từ khóa/request và chỉ số 0–100 chỉ mang tính tương đối nội bộ từng request.
   * Hệ thống áp dụng kỹ thuật **Anchor Keyword** (`Công nghệ thông tin` làm từ khóa mốc xuyên suốt). Tỷ lệ scale factor giữa các cụm từ khóa được tự động tính toán bằng **Robust Median Ratio**, đưa toàn bộ dữ liệu về **cùng một hệ quy chiếu [0, 100] toàn cục** phục vụ cho các mô hình Machine Learning (XGBoost / Fuzzy Inference Systems).
2. **Kháng Rate-Limit & Chống Bot (HTTP 429)**:
   * Khắc phục triệt để lỗi không tương thích giữa `pytrends` và `urllib3 >= 2.0` (`method_whitelist`).
   * Áp dụng **Exponential Backoff with Jitter** và tự động refresh session / payload khi gặp giới hạn tần suất từ Google.
3. **Cơ chế Checkpoint & Fault Tolerance**:
   * Tự động ghi nhận lịch sử vào `data/lake/raw/checkpoints/scrape_checkpoint.json`. Nếu chạy lại, hệ thống đọc từ cache và chỉ cào các batch còn thiếu.
4. **Kiến trúc Storage Chuẩn Data Engineering**:
   * **Data Lake Raw** (`data/lake/raw/`): Lưu song song định dạng **Parquet** (cho Apache Spark) và **CSV/JSON** (cho kiểm tra thủ công).
   * **Master Normalized Zone** (`data/lake/normalized/`): Bảng dữ liệu chuỗi thời gian và vùng miền đã được chuẩn hóa liên cụm từ khóa.
   * **Data Warehouse** (`data/warehouse/trends.duckdb`): Cơ sở dữ liệu DuckDB hiệu năng cao, hỗ trợ truy vấn SQL tốc độ cao.

---

## 3. Hướng dẫn Vận hành Hệ thống

### 3.1. Cài đặt môi trường
```bash
pip install -r requirements.txt
```

### 3.2. Thu thập Dữ liệu theo Khung Thời gian Linh hoạt

* **Cào khung 5 năm qua (`5y` - 262 tuần, Mặc định cho đề tài)**:
  ```bash
  python run_scraper.py --all
  ```
* **Cào khung 1 năm qua (`1y` - 53 tuần)**:
  ```bash
  python run_scraper.py --all --timeframe 1y
  ```
* **Cào khung 3 tháng qua (`3m` - 93 ngày chi tiết theo từng ngày)**:
  ```bash
  python run_scraper.py --all --timeframe 3m
  ```
* **Cào riêng từng danh mục cụ thể**:
  ```bash
  python run_scraper.py --category majors_it --timeframe 1y
  python run_scraper.py --category universities_it
  python run_scraper.py --category admission_signals
  python run_scraper.py --category job_market_signals
  ```
* **Ép cào mới lại từ đầu (Bỏ qua checkpoint cache)**:
  ```bash
  python run_scraper.py --all --force
  ```

### 3.3. Xem và Truy vấn Dữ liệu

* **Cách 1: Xem nhanh qua Terminal bằng script tương tác**:
  ```bash
  python view_duckdb.py
  ```
* **Cách 2: Mở Jupyter Notebook phân tích EDA & biểu đồ**:
  Mở tệp `notebooks/01_google_trends_analysis.ipynb` trong VS Code và nhấn **Run All**.

---

## 4. BẢN CHẤT TOÁN HỌC & GIẢI TRÌNH SAI LỆCH DỮ LIỆU GOOGLE TRENDS

Phần này đặc biệt quan trọng phục vụ cho việc **báo cáo đề tài và phản biện khoa học**:

### 4.1. Công thức Chuẩn hóa của Google Trends (Normalization Formula)
Google Trends **không bao giờ trả về số lượt tìm kiếm tuyệt đối**, mà tính theo công thức tỷ lệ phần trăm tương đối:

$$\text{Điểm số tuần } t = \frac{\text{Lượng tìm kiếm của tuần } t}{\text{Lượng tìm kiếm của tuần CAO NHẤT trong khung thời gian được chọn}} \times 100$$

#### 👉 Giải thích sự khác biệt con số giữa khung 5 năm (`5y`) và khung 1 năm (`1y`):
* **Khi chọn khung 1 năm (`1y`)**:
  * Mẫu số là tuần cao nhất của **riêng 1 năm đó** (tuần 09/08/2026).
  * Vì nó cao nhất trong năm đó nên điểm số của nó đạt mốc **`100`**.
* **Khi chọn khung 5 năm (`5y`)**:
  * Mẫu số là tuần cao nhất của **cả 5 năm** (rơi vào tháng 7 năm 2022).
  * So với đỉnh kỷ lục năm 2022, tuần 09/08/2026 chỉ đạt **`74%`** $\rightarrow$ Điểm trong file 5 năm là **`74`**.
* **Kết luận**: Hình dáng đồ thị, các điểm uốn, tỷ lệ tăng giảm giữa các tuần là **trùng khớp 100%**. Con số chỉ bị co giãn trục tung theo tỷ lệ mẫu số quy đổi ($74 / 100 = 0.74$).

---

### 4.2. Giải thích Dung sai $\pm 1$ Đơn vị (Tolerance $\pm 1$)
Khi đối chiếu một tuần cụ thể giữa file cào và giao diện web (ví dụ: `50` so với `51`, hay `54` so với `55`), sự chênh lệch $\pm 1$ đơn vị xuất phát từ 2 nguyên nhân kỹ thuật:

1. **Cơ chế Lấy mẫu ngẫu nhiên của Google (Sampling-based Estimation)**:
   * Google xử lý hàng tỷ lượt tìm kiếm mỗi ngày. Để phản hồi trong 0.5s, Google **không quét toàn bộ database mà lấy một mẫu ngẫu nhiên không thiên lệch (unbiased sample)**.
   * Tài liệu chính thức của Google: *"Google Trends data is an unbiased sample of Google search data. The sample is refreshed regularly."*
   * Hai lần truy vấn khác thời điểm (hoặc giữa web UI và API) lấy 2 mẫu vi mô hơi khác nhau $\rightarrow$ Tạo độ lệch tự nhiên $\pm 1\%$.
2. **Phép làm tròn số thực (Floating-point Rounding)**:
   * Dữ liệu gốc bên dưới Google tính ra số thực (ví dụ `50.49` hoặc `54.51`).
   * Giao diện web JavaScript làm tròn lên (`Math.round` / `Math.ceil`) thành `51` hoặc `55`.
   * Thư viện Python/Pandas làm tròn chuẩn ngân hàng (`round half to even`) thành `50` hoặc `54`.

#### ⚠️ Đánh giá ảnh hưởng đến Machine Learning:
* **Hoàn toàn không ảnh hưởng**: Sai số $\pm 1\%$ chỉ là nhiễu đo lường vi mô (measurement noise $< 1\%$).
* Các mô hình Machine Learning (XGBoost, Random Forest, Fuzzy Inference) quan tâm đến **tín hiệu hình dáng xu hướng (Trend & Momentum)**: sự bùng nổ của mùa thi (tăng vọt từ `30` lên `100`), tính chu kỳ lặp lại hàng năm, và độ chênh lệch giữa các ngành đào tạo. Các bộ chuẩn hóa dữ liệu (`MinMaxScaler`, `StandardScaler`) sẽ tự động triệt tiêu sai số này.

---

### 4.3. Quy tắc Lọc Từ khóa Tránh Nhiễu (Data Cleaning & Taxonomy)
Để đảm bảo tín hiệu dữ liệu phản ánh chính xác nhất ý định xét tuyển của thí sinh:
* **Không dùng từ viết tắt quá ngắn hoặc đa nghĩa đứng độc lập**:
  * ❌ `AI`: Dễ bị lẫn với phần mềm đồ họa *Adobe Illustrator* hoặc vị trí công việc *AI Engineer*.  
    $\rightarrow$ ✅ Thay bằng cụm rõ nghĩa: `Trí tuệ nhân tạo`.
  * ❌ `FPT`: Dễ bị lẫn với *FPT Shop* (mua điện thoại) hoặc *FPT Telecom* (đóng tiền cước).  
    $\rightarrow$ ✅ Luôn gắn liền chữ trường: `Đại học FPT`.
  * ❌ `Developer`: Dễ bị lẫn với công việc đang làm.  
    $\rightarrow$ ✅ Thay bằng: `Lập trình viên`, `Việc làm IT`, `Kỹ sư phần mềm`.
* **Luôn gắn từ khóa trường với định danh học thuật**:
  * Sử dụng `Đại học Bách Khoa`, `Đại học Công nghệ Thông tin`, `Đại học Khoa học Tự nhiên`, `Học viện Bưu chính Viễn thông`...

---

## 5. Kết nối Pipeline Trích xuất Đặc trưng (PySpark Integration)

Theo kiến trúc Data Lakehouse, tệp Parquet master được nạp trực tiếp vào PySpark Session để phục vụ các bước Feature Engineering và Model Training tiếp theo:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("AdmissionPrediction_TrendsIngestion") \
    .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
    .getOrCreate()

# Đọc bảng Master Parquet từ Data Lake
df_spark = spark.read.parquet("data/lake/normalized/master_trends_majors_it.parquet")
df_spark.printSchema()
df_spark.show(5)
```
