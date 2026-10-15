# Big Data project

## Cấu trúc dự án

- `config\dirs.yaml`: Danh mục các path. Mọi path đều phải được đăng ký trong này và dùng bằng `helpers\get_configs.py`.
- `data-raw`: Chứa các file `.csv` **CHƯA** cleaned (thu trực tiếp từ fetching).
- `data-cleaned`: Chứa các file `.csv` đã cleaned.
- `scripts-fetching`: Chứa các file notebook và unit-script (export từ notebook thông qua `helpers\export_to_script.py`) thu thập dữ liệu.
- `scripts-processing`: Chứa các file notebook và unit-script (export từ notebook thông qua `helpers\export_to_script.py`) làm sạch dữ liệu.
- `helpers`: Chứa các hàm helper trợ giúp làm việc với notebook và script.

## Quy tắc

- Mọi path đều cấu hình trung gian qua `config\dirs.yaml`.
- Phong cách lập trình notebook và unit scripts là hướng cấu trúc (structural oriented), không phải OOP.
- Đánh dấu `# export` trước mỗi node có thể xuất ra thành script chính.
- Mọi dependency hữu ích cần được khai báo trong `requirements.txt`.

## Shortcuts

_Note_: Nên kích hoạt venv và chỉ làm việc trong môi trường venv.

Kích hoạt môi trường venv (Windows):

```sh
.venv\Scripts\activate
```

Tải dependencies:

```sh
pip install -r requirements.txt
```

Cài đặt Chromium browser driver (nếu cần sử dụng `helpers\crawl_trend_data.py` - Playwright):

```sh
playwright install chromium
```

## Thu thập Google Trends

Pipeline chính nằm tại `scripts-fetching/unit-scripts/get_trends.py`. Pipeline
lọc một topic tốt nhất cho mỗi cặp `keyword`/`keyword_type`; nếu topic không đủ
liên quan, nó dùng chính keyword thay vì một `mid` sai. Các query trùng nhau được
gom lại và vẫn giữ đầy đủ `keyword_metadata`.

Kiểm tra quá trình chọn topic mà không gửi request tới Google:

```powershell
python .\scripts-fetching\unit-scripts\get_trends.py --validate-only
```

Với dữ liệu hiện tại, cấu hình mặc định giảm 2.683 `mid` xuống 879 query duy
nhất: 559 topic MID và 320 keyword fallback.

### Cách chạy khuyến nghị

Chạy stage Interest over time trước:

```powershell
python .\scripts-fetching\unit-scripts\get_trends.py `
  --stage interest `
  --geo VN `
  --min-request-interval 10
```

Sau khi stage trên hoàn tất, lấy region và Top/Rising queries cho tối đa 200
query có tín hiệu và độ liên quan topic cao nhất:

```powershell
python .\scripts-fetching\unit-scripts\get_trends.py `
  --stage enrichment `
  --geo VN `
  --max-enrich 200 `
  --min-request-interval 10
```

Có thể chạy cả hai stage bằng một lệnh:

```powershell
python .\scripts-fetching\unit-scripts\get_trends.py --stage all --geo VN
```

Chạy thử 20 query:

```powershell
python .\scripts-fetching\unit-scripts\get_trends.py --stage interest --geo VN --limit 20
```

`geo='VI'` vẫn là mặc định để tương thích yêu cầu ban đầu, nhưng `VI` là U.S.
Virgin Islands. Nếu mục tiêu là Việt Nam, cần truyền `--geo VN` như các ví dụ
trên.

### Cache, resume và HTTP 429

Mỗi stage thành công được ghi ngay vào
`data-raw/google-trends/trends-cache.sqlite3`. Khi chạy lại cùng cấu hình, script
đọc cache và không gọi lại các batch đã hoàn tất. Kết quả tổng hợp cuối cùng vẫn
là một JSON array duy nhất tại `data-raw/google-trends/trends.json`.

Pipeline chạy tuần tự và mặc định cách mỗi HTTP request ít nhất 10 giây. Nếu
Google trả HTTP 429, circuit breaker dừng tiến trình ngay, ghi JSON từ cache và
thoát mà không retry 429 hoặc chờ worker nền. Hãy chờ hết giới hạn rồi chạy lại
cùng lệnh để tiếp tục.

Nhấn `Ctrl+C` cũng dừng sạch và ghi lại kết quả từ cache, không xuất traceback
từ `ThreadPoolExecutor`.

Xóa cache khi thực sự muốn thu thập lại từ đầu:

```powershell
python .\scripts-fetching\unit-scripts\get_trends.py --clear-cache --validate-only
```

Kiểm thử offline:

```powershell
python -m unittest discover -s test -p "test_get_trends.py" -v
```

Mỗi object đầu ra có `query`, `query_kind` (`topic_mid` hoặc `search_term`),
`mid`, metadata keyword, `stage_status`, `interest_over_time`,
`interest_by_region` và `commonly_searched_queries`. Query không đủ tín hiệu
được giữ với `status='interest_only'` và lý do bỏ qua enrichment; query chưa
hoàn tất do 429 có `status='pending'` để lần chạy sau tiếp tục.
