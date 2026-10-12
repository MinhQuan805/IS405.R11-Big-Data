# HƯỚNG DẪN SỬ DỤNG VÀ TÀI LIỆU KỸ THUẬT
## Module: `helpers.crawl_trend_data` (Google Trends Playwright Crawler)

Module `helpers.crawl_trend_data` cung cấp giải pháp cào và trích xuất dữ liệu tự động từ **Google Trends** (`https://trends.google.com/explore`) bằng Playwright. Module được thiết kế hoàn chỉnh với cơ chế chống chặn bot (stealth evasion), bắt tải file CSV trực tiếp, fallback phân tích DOM, tự động thử lại khi gặp giới hạn tần suất (Rate Limit 429), và hỗ trợ xuất dữ liệu ra cả định dạng JSON lẫn Pandas DataFrame.

---

## 1. Điều Kiện Tiên Quyết & Cài Đặt (Prerequisites & Installation)

Module yêu cầu Python 3.9+ và thư viện trình duyệt Playwright.

### Bước 1: Cài đặt thư viện Python
Trong môi trường ảo của dự án (`.venv`), cài đặt các dependencies:
```bash
pip install playwright pandas
```

### Bước 2: Tải trình duyệt Playwright (Chromium)
Playwright yêu cầu tải binary của trình duyệt để vận hành:
```bash
playwright install chromium
```
*(Nếu làm việc trên máy Windows có sẵn Google Chrome, crawler sẽ tự động ưu tiên gọi Chrome hệ thống để giảm thiểu tối đa khả năng bị Google nhận diện).*

---

## 2. Chi Tiết Tham Số Đầu Vào Của Hàm `crawl_trend_data(...)`

Cú pháp hàm:
```python
def crawl_trend_data(
    q: Union[str, List[str]],
    date: Union[GoogleDateRange, str] = GoogleDateRange.PAST_12_MONTHS,
    geo: Union[GoogleGeo, str] = GoogleGeo.VIETNAM,
    headless: bool = True,
    timeout: int = 35000,
    max_retries: int = 3,
    retry_delay: float = 3.0,
    export_dir: Optional[str] = None,
    offline_html_path: Optional[str] = None
) -> GoogleTrendResult:
```

### Bảng Giải Thích Chi Tiết Tham Số

| Tham số | Kiểu dữ liệu | Mặc định | Mô tả chi tiết |
| :--- | :--- | :--- | :--- |
| `q` | `str` hoặc `List[str]` | *(Bắt buộc)* | Từ khóa tìm kiếm đơn lẻ (ví dụ: `"python"`) hoặc danh sách các từ khóa so sánh (ví dụ: `["python", "java", "rust"]`). Google Trends hỗ trợ so sánh **tối đa 5 từ khóa**; nếu truyền quá 5, crawler sẽ tự động lấy 5 từ khóa đầu tiên và ghi log cảnh báo. |
| `date` | `GoogleDateRange` hoặc `str` | `GoogleDateRange.PAST_12_MONTHS` | Khoảng thời gian tìm kiếm. Chấp nhận các Enum định sẵn, token tương đối (`"today 12-m"`, `"all"`), hoặc khoảng ngày tùy chỉnh (`"2010-01-01 2026-10-13"`, `"2010-01-01%202026-10-13"`). |
| `geo` | `GoogleGeo` hoặc `str` | `GoogleGeo.VIETNAM` (`"VN"`) | Mã vùng địa lý theo chuẩn ISO 3166-1 alpha-2. Sử dụng `GoogleGeo.WORLDWIDE` hoặc chuỗi rỗng `""` nếu muốn tìm kiếm trên toàn thế giới. |
| `headless` | `bool` | `True` | Chạy trình duyệt ẩn danh không hiển thị giao diện (`True`). Đặt thành `False` khi muốn quan sát trực tiếp trình duyệt trên màn hình (hữu ích khi debug hoặc vượt captcha). |
| `timeout` | `int` | `35000` (ms) | Thời gian chờ tối đa (tính bằng mili-giây) cho các hành động tải trang và chờ widget (mặc định 35 giây). |
| `max_retries` | `int` | `3` | Số lần thử lại tối đa khi gặp lỗi mạng, trang bị timeout hoặc Google phản hồi mã `429 Too Many Requests`. |
| `retry_delay` | `float` | `3.0` (giây) | Thời gian chờ cơ sở cho thuật toán exponential backoff kết hợp ngẫu nhiên hóa (jitter) giữa các lần thử lại. |
| `export_dir` | `Optional[str]` | `None` | Đường dẫn thư mục để lưu trữ các file `.csv` gốc mà Google Trends tạo ra khi tải xuống (nếu cần lưu trữ thô). |
| `offline_html_path`| `Optional[str]` | `None` | Đường dẫn đến file HTML snapshot cục bộ (ví dụ: `"Explore - Google Trends.html"`). Nếu truyền vào, crawler sẽ bóc tách trực tiếp từ file này mà không cần kết nối mạng. |

---

## 3. Quy Định Sử Dụng Tham Số `date` (Date Range)

Module hỗ trợ toàn diện các định dạng thời gian của Google Trends:

### A. Khoảng ngày tùy chỉnh (Custom Date Range):
Tự động chuẩn hóa và giải mã URL để tránh lỗi double-encoding (`%2520`):

* **Chuỗi có mã hóa URL (`%20`):**
  ```python
  crawl_trend_data(q="python", date="2010-01-01%202026-10-13")
  ```
* **Chuỗi có dấu cách thông thường:**
  ```python
  crawl_trend_data(q="python", date="2010-01-01 2026-10-13")
  ```
* **Sử dụng phương thức trợ giúp `GoogleDateRange.custom(start, end)`:**
  ```python
  crawl_trend_data(
      q="python",
      date=GoogleDateRange.custom("2010-01-01", "2026-10-13")
  )
  ```

### B. Các mốc thời gian tương đối chuẩn (`GoogleDateRange` Enum):

| Enum | Chuỗi tương đương | Ý nghĩa |
| :--- | :--- | :--- |
| `GoogleDateRange.PAST_HOUR` | `"now 1-H"` | 1 giờ qua |
| `GoogleDateRange.PAST_4_HOURS` | `"now 4-H"` | 4 giờ qua |
| `GoogleDateRange.PAST_DAY` | `"now 1-d"` | 1 ngày qua (24 giờ) |
| `GoogleDateRange.PAST_7_DAYS` | `"now 7-d"` | 7 ngày qua |
| `GoogleDateRange.PAST_30_DAYS` | `"today 1-m"` | 30 ngày qua (1 tháng) |
| `GoogleDateRange.PAST_90_DAYS` | `"today 3-m"` | 90 ngày qua (3 tháng) |
| `GoogleDateRange.PAST_12_MONTHS` | `"today 12-m"` | 12 tháng qua (1 năm) - *Mặc định* |
| `GoogleDateRange.PAST_5_YEARS` | `"today 5-y"` | 5 năm qua |
| `GoogleDateRange.ALL_TIME` | `"all"` | Từ 2004 đến hiện tại |

---

## 4. Danh Sách Mã Địa Lý (`GoogleGeo` Enum)

| Enum | Mã ISO | Quốc gia / Vùng lãnh thổ |
| :--- | :--- | :--- |
| `GoogleGeo.VIETNAM` | `"VN"` | Việt Nam *(Mặc định)* |
| `GoogleGeo.WORLDWIDE` | `""` | Toàn thế giới |
| `GoogleGeo.UNITED_STATES` | `"US"` | Hoa Kỳ |
| `GoogleGeo.UNITED_KINGDOM` | `"GB"` | Vương quốc Anh |
| `GoogleGeo.JAPAN` | `"JP"` | Nhật Bản |
| `GoogleGeo.SOUTH_KOREA` | `"KR"` | Hàn Quốc |
| `GoogleGeo.SINGAPORE` | `"SG"` | Singapore |
| `GoogleGeo.GERMANY` | `"DE"` | Đức |
| `GoogleGeo.FRANCE` | `"FR"` | Pháp |
| `GoogleGeo.AUSTRALIA` | `"AU"` | Úc |
| `GoogleGeo.CANADA` | `"CA"` | Canada |
| `GoogleGeo.INDIA` | `"IN"` | Ấn Độ |
| `GoogleGeo.THAILAND` | `"TH"` | Thái Lan |
| `GoogleGeo.INDONESIA` | `"ID"` | Indonesia |
| `GoogleGeo.MALAYSIA` | `"MY"` | Malaysia |

*(Bạn cũng có thể truyền trực tiếp bất kỳ mã quốc gia 2 ký tự ISO 3166-1 nào dưới dạng chuỗi, ví dụ: `geo="JP"`).*

---

## 5. Hướng Dẫn Gọi Hàm Từ Script Khác (Python Code Examples)

### Ví dụ 1: Cào cơ bản 1 từ khóa với thiết lập mặc định
```python
from helpers.crawl_trend_data import crawl_trend_data

# Cào dữ liệu từ khóa 'python' tại Việt Nam trong 12 tháng qua
result = crawl_trend_data(q="python")

print(f"Trạng thái: {result.status}")
if result.interest_over_time:
    print(f"Số điểm mốc thời gian: {len(result.interest_over_time.timeline)}")
    print(f"Điểm quan tâm trung bình: {result.interest_over_time.average_interest}")
```

---

### Ví dụ 2: So sánh nhiều từ khóa trên phạm vi toàn cầu
```python
from helpers.crawl_trend_data import crawl_trend_data, GoogleGeo, GoogleDateRange

# So sánh 3 công nghệ trên toàn thế giới trong 5 năm qua
result = crawl_trend_data(
    q=["python", "rust", "golang"],
    date=GoogleDateRange.PAST_5_YEARS,
    geo=GoogleGeo.WORLDWIDE,
    headless=True
)

# Hiển thị điểm quan tâm trung bình từng ngôn ngữ
print("Điểm trung bình:", result.interest_over_time.average_interest)
```

---

### Ví dụ 3: Cào theo khoảng thời gian tùy chỉnh (`date=2010-01-01%202026-10-13`)
```python
from helpers.crawl_trend_data import crawl_trend_data, GoogleDateRange

# Truyền chuỗi date đã mã hóa URL %20
result = crawl_trend_data(
    q=["machine learning", "deep learning"],
    date="2010-01-01%202026-10-13",
    geo="US"
)

# Hoặc dùng helper function:
# date=GoogleDateRange.custom("2010-01-01", "2026-10-13")

print(f"Khoảng thời gian: {result.date_range}")
print(f"Số dòng dữ liệu thu được: {len(result.interest_over_time.timeline)}")
```

---

### Ví dụ 4: Xuất ra Pandas DataFrame và lưu trữ vào Data Lake / File
```python
import os
from helpers.crawl_trend_data import crawl_trend_data

result = crawl_trend_data(q="chatgpt", geo="VN")

# 1. Xuất chuỗi JSON UTF-8
json_data = result.to_json(indent=2)
with open("chatgpt_trends.json", "w", encoding="utf-8") as f:
    f.write(json_data)

# 2. Xuất thành 4 bảng Pandas DataFrame
dfs = result.to_dataframes()

df_timeline = dfs["timeline"]       # Bảng chuỗi thời gian
df_region = dfs["region"]           # Bảng phân bố tỉnh thành
df_top = dfs["top_queries"]         # Bảng top từ khóa tìm kiếm
df_rising = dfs["rising_queries"]   # Bảng từ khóa đột biến

print(df_timeline.head())
print(df_rising.head())

# Lưu trực tiếp ra CSV hoặc Parquet cho Spark
os.makedirs("data-cleaned", exist_ok=True)
df_timeline.to_csv("data-cleaned/chatgpt_timeline.csv", index=False)
```

---

### Ví dụ 5: Bật trình duyệt có giao diện (`headless=False`) và lưu file CSV gốc
```python
from helpers.crawl_trend_data import crawl_trend_data

# Mở cửa sổ trình duyệt để quan sát và lưu toàn bộ CSV được tải về
result = crawl_trend_data(
    q="big data",
    geo="VN",
    headless=False,           # Mở cửa sổ Chromium trực quan
    export_dir="data-raw/csv" # Tự động lưu các file CSV tải về vào thư mục này
)
```

---

### Ví dụ 6: Sử dụng chế độ Class hướng đối tượng (`GoogleTrendsCrawler`)
Nếu muốn tái sử dụng đối tượng crawler với các cấu hình nâng cao hoặc proxy:
```python
from helpers.crawl_trend_data import GoogleTrendsCrawler, GoogleDateRange

crawler = GoogleTrendsCrawler(
    headless=True,
    timeout=40000,
    max_retries=3,
    retry_delay=5.0,
    proxy={"server": "http://user:pass@proxy-ip:port"}, # Nếu dùng proxy xoay vòng
    export_dir="raw_downloads"
)

res = crawler.crawl(
    q=["spark", "hadoop"],
    date=GoogleDateRange.PAST_5_YEARS,
    geo="VN"
)
```

---

## 6. Hướng Dẫn Sử Dụng Bằng Dòng Lệnh (CLI Usage)

Module hỗ trợ chạy trực tiếp từ dòng lệnh thông qua file `helpers/crawl_trend_data.py`.

### Danh sách cờ lệnh (CLI Arguments):
* `--q`: Một hoặc nhiều từ khóa tìm kiếm (phân cách bằng khoảng trắng).
* `--date`: Khoảng thời gian (chấp nhận cả `today 12-m`, `2010-01-01 2026-10-13`, `2010-01-01%202026-10-13`).
* `--geo`: Mã vùng địa lý (`VN`, `US`, `""` cho toàn cầu).
* `--headed`: Chạy ở chế độ hiển thị cửa sổ trình duyệt (mặc định là headless).
* `--out`: Đường dẫn file JSON để ghi kết quả ra đĩa.
* `--offline`: Đường dẫn file snapshot HTML để chạy thử nghiệm ngoại tuyến.

### Các câu lệnh mẫu:

```bash
# 1. Cào 1 từ khóa với ngày tùy chỉnh (URL-encoded %20)
python helpers/crawl_trend_data.py --q python --date "2010-01-01%202026-10-13" --geo VN --out output.json

# 2. Cào so sánh nhiều từ khóa với mốc thời gian 5 năm
python helpers/crawl_trend_data.py --q python golang rust --date "today 5-y" --geo VN --out compare.json

# 3. Bật cửa sổ trình duyệt (Headed mode)
python helpers/crawl_trend_data.py --q "deepseek" --geo VN --headed

# 4. Chạy phân tích offline từ file HTML snapshot
python helpers/crawl_trend_data.py --q python --offline "Explore - Google Trends.html" --out offline_result.json
```

---

## 7. Cơ Chế Chống Chặn Bot, Thử Lại (Retry) & Tự Động Phục Hồi

1. **Che giấu danh tính trình duyệt (Stealth Evasion)**:
   * Loại bỏ cờ tự động hóa `navigator.webdriver`.
   * Giả lập danh sách plugin và ngôn ngữ chuẩn của người dùng thật.
   * Xoay vòng User-Agent thực tế từ các trình duyệt hiện đại.
   * Khởi chạy với Chrome thật của hệ điều hành nếu có sẵn.
2. **Xử lý Consent Modal & Overlay**:
   * Tự động nhận diện và đóng các popup *"Try the new Explore page"*, cookie banner *"Before you continue to Google"*.
   * Giữ phiên duyệt ở trang `/explore` thay vì bị chuyển hướng sang `/trends/explore` cũ (vốn dễ bị lỗi HTTP 429).
3. **Cơ chế tải dữ liệu kép (Dual Extraction Strategy)**:
   * **Chiến lược chính**: Tự động kích hoạt các nút download CSV trên từng widget của Google Trends để lấy dữ liệu số học chính xác tuyệt đối.
   * **Chiến lược phụ (DOM Fallback)**: Nếu Google chặn download CSV, crawler tự động duyệt cây DOM của widget để trích xuất số liệu bảng và danh sách từ khóa.
4. **Xử lý giới hạn tần suất (Rate Limiting & Exponential Backoff)**:
   * Nhận diện mã HTTP 429 hoặc thông báo giới hạn tần suất.
   * Tự động ngắt kết nối và áp dụng thuật toán lũy thừa cơ số 2 kết hợp ngẫu nhiên hóa thời gian chờ (Exponential Backoff with Jitter) trước khi thử lại ở lần tiếp theo.
5. **Cơ chế tự phục hồi ngoại tuyến (Auto-Recovery Fallback)**:
   * Nếu cả 3 lần thử trực tuyến đều bị chặn bởi tường lửa Google, crawler sẽ tự động tìm kiếm snapshot HTML có sẵn trong thư mục dự án (`Explore - Google Trends.html`) để trích xuất dữ liệu dự phòng, trả về kết quả kèm `status: "partial"` thay vì làm dừng toàn bộ pipeline dữ liệu.

---

## 8. Tài Liệu Cấu Trúc Dữ Liệu Đầu Ra (Output Format & Schema)

### 8.1. Cấu Trúc JSON Schema Hoàn Chỉnh

```json
{
  "query_terms": ["python", "java"],
  "date_range": "2010-01-01 2026-10-13",
  "geo": "VN",
  "scraped_at": "2026-10-13T00:19:55.123456",
  "status": "success",
  "errors": [],
  "metadata": {
    "url": "https://trends.google.com/explore?q=python%2Cjava&hl=en&date=2010-01-01%202026-10-13&geo=VN",
    "attempt": 1,
    "widgets_detected": true
  },

  "interest_over_time": {
    "queries": ["python", "java"],
    "timeline": [
      {
        "date": "2025-10-19",
        "values": {
          "python": 85,
          "java": 42
        }
      },
      {
        "date": "2025-10-26",
        "values": {
          "python": 88,
          "java": 39
        }
      }
    ],
    "average_interest": {
      "python": 81.4,
      "java": 44.2
    },
    "data_source": "csv"
  },

  "interest_by_region": {
    "queries": ["python", "java"],
    "regions": [
      {
        "region": "Ho Chi Minh City",
        "rank": 1,
        "values": {
          "python": 70,
          "java": 30
        }
      },
      {
        "region": "Hanoi",
        "rank": 2,
        "values": {
          "python": 65,
          "java": 35
        }
      }
    ],
    "data_source": "csv"
  },

  "commonly_searched_queries": {
    "top_queries": {
      "python": [
        {
          "rank": 1,
          "query": "python download",
          "value": 100,
          "is_breakout": false,
          "metric_type": "score"
        },
        {
          "rank": 2,
          "query": "python online",
          "value": 85,
          "is_breakout": false,
          "metric_type": "score"
        }
      ]
    },
    "rising_queries": {
      "python": [
        {
          "rank": 1,
          "query": "deepseek python",
          "value": "Breakout",
          "is_breakout": true,
          "metric_type": "change"
        },
        {
          "rank": 2,
          "query": "chatgpt python api",
          "value": "+350%",
          "is_breakout": false,
          "metric_type": "change"
        }
      ]
    },
    "data_source": "mixed"
  }
}
```

---

### 8.2. Ý Nghĩa Chi Tiết Từng Trường (Field Descriptions)

| Trường (Field) | Kiểu dữ liệu | Ý nghĩa |
| :--- | :--- | :--- |
| `query_terms` | `List[str]` | Danh sách các từ khóa so sánh (tối đa 5 từ). |
| `date_range` | `str` | Mốc thời gian tìm kiếm chuẩn hóa. |
| `geo` | `str` | Mã vùng địa lý ISO (ví dụ: `"VN"`, `"US"`, `""` cho toàn cầu). |
| `scraped_at` | `str` (ISO 8601) | Thời điểm thực hiện cào dữ liệu (UTC). |
| `status` | `str` | Trạng thái kết quả: `"success"` (đầy đủ cả 3 widget), `"partial"` (thu thập được 1 phần), `"failed"` (lỗi hoàn toàn). |
| `errors` | `List[str]` | Danh sách thông báo lỗi hoặc cảnh báo ghi nhận trong quá trình chạy. |
| **`interest_over_time`** | `InterestOverTimeData` | Dữ liệu mức độ quan tâm theo thời gian. |
| ↳ `timeline` | `List[TimelinePoint]` | Mảng các mốc thời gian (`date`: ngày/tuần/tháng, `values`: điểm số từ 0 - 100 theo từng từ khóa). |
| ↳ `average_interest` | `Dict[str, float]` | Điểm số quan tâm trung bình của từng từ khóa trong khoảng thời gian. |
| **`interest_by_region`** | `InterestByRegionData` | Mức độ quan tâm phân bố theo khu vực/tỉnh thành. |
| ↳ `regions` | `List[RegionInterestItem]` | Danh sách khu vực (`region`: tên tỉnh/bang, `rank`: thứ hạng, `values`: tỷ lệ % hoặc điểm số). |
| **`commonly_searched_queries`** | `CommonlySearchedQueriesData`| Các truy vấn tìm kiếm liên quan (phân nhóm theo từng từ khóa gốc). |
| ↳ `top_queries` | `Dict[str, List[QueryItem]]` | Các truy vấn phổ biến nhất (điểm từ 0 - 100). |
| ↳ `rising_queries` | `Dict[str, List[QueryItem]]` | Các truy vấn gia tăng đột biến (`value`: tỷ lệ tăng trưởng hoặc `"Breakout"` nếu tăng $\ge 5000\%$). |

---

### 8.3. Cấu Trúc Khi Xuất Sang Pandas DataFrame (`result.to_dataframes()`)

Đối với các pipeline xử lý dữ liệu lớn (Spark/Pandas), phương thức `result.to_dataframes()` trả về một `dict` gồm 4 DataFrame đã được chuẩn hóa cột:

1. **`dfs["timeline"]`**:
   * Cột: `['date', '<query_1>', '<query_2>', ...]`
   * Dùng để trực quan hóa đồ thị xu hướng thời gian (Line Chart / Time Series).
2. **`dfs["region"]`**:
   * Cột: `['region', 'rank', '<query_1>', '<query_2>', ...]`
   * Dùng để xây dựng bản đồ nhiệt theo tỉnh thành/quốc gia (Choropleth Map).
3. **`dfs["top_queries"]`**:
   * Cột: `['search_term', 'rank', 'query', 'value']`
   * Dùng để phân tích các chủ đề/từ khóa phổ biến đi kèm.
4. **`dfs["rising_queries"]`**:
   * Cột: `['search_term', 'rank', 'query', 'value', 'is_breakout']`
   * Dùng để phát hiện sớm các xu hướng bùng nổ (Breakout Trends).