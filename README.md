# Big Data project

**Mục đích của tài liệu này**:

- Giới thiệu về mục tiêu dự án, cấu trúc dự án, các hướng dẫn và ghi chú quan trọng khi sử dụng dự án.
- Tài liệu này chỉ được phép thay đổi khi có sự đồng ý từ dev.

## Cấu trúc dự án

- `config\dirs.yaml`: Danh mục các path. Mọi path đều phải được đăng ký trong này và dùng bằng `helpers\get_configs.py`.
- `data-raw`: Chứa các file `.csv` **CHƯA** cleaned (thu trực tiếp từ fetching).
- `data-cleaned`: Chứa các file `.csv` đã cleaned.
- `scripts-fetching`: Chứa các file notebook và unit-script (export từ notebook thông qua `helpers\export_to_script.py`) thu thập dữ liệu.
- `scripts-processing`: Chứa các file notebook và unit-script (export từ notebook thông qua `helpers\export_to_script.py`) làm sạch dữ liệu.
- `helpers`: Chứa các hàm helper trợ giúp làm việc với notebook và script.
- `docs`: Chứa các tài liệu (ưu tiên `.md`).

## Quy tắc

- Mọi path đều cấu hình trung gian qua `config\dirs.yaml`.
- Phong cách lập trình notebook và unit scripts là hướng cấu trúc (structural oriented), không phải OOP.
- Đánh dấu `# export` trước mỗi node có thể xuất ra thành script chính.
- Mọi dependency có tính tái sử dụng cần được khai báo trong `requirements.txt`.
- Sử dụng `dtype_backend` mặc định cho `pd.read_parquet`.
- Luôn mã hóa Unicode khi đọc / ghi.
- Các file `.csv` để phải chuyển thành `.parquet` thông qua `pd.to_parquet` hoặc thông qua helper `helpers\convert_to_parquet.py`:

Snippet:

```sh
-- Chuyển đổi các .csv trong 1 folder thành parquet (giữ lại .csv gốc)
python helpers/convert_to_parquet.py data-cleaned

-- Thay thế .csv gốc
python helpers/convert_to_parquet.py data-raw/admission-cutoff-score/majors.csv --inplace
```

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

## Một số VSCode extension hữu ích nên cài thêm (dành cho dev)

- **Parquet Explorer** (_Adam Viola_): Explore Parquet files with SQL. Powered by DuckDB.
