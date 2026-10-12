# Big Data project

## Cấu trúc dự án

- `config\dirs.yaml`: Danh mục các path. Mọi path đều phải được đăng ký trong này và dùng bằng `helpers\get_configs.py`.
- `data-raw`: Chứa các file `.csv` **CHƯA** cleaned (thu trực tiếp từ fetching).
- `data-cleaned`: Chứa các file `.csv` đã cleaned.
- `scripts-fetching`: Chứa các file notebook và unit-script (export từ notebook thông qua `helpers\export_to_script.py`) thu thập dữ liệu.
- `scripts-processing`: Chứa các file notebook và unit-script (export từ notebook thông qua `helpers\export_to_script.py`) làm sạch dữ liệu.
- `helpers`: Chứa các hàm helper trợ giúp làm việc với notebook và script.

## Quy tắc

- Mọi path và các thông số khác đều cấu hình trung gian qua `config/`.
- Phong cách lập trình notebook và unit scripts là hướng cấu trúc (structural oriented), không phải OOP.
- Đánh dấu `# export` trước mỗi node có thể xuất ra thành script chính.
- Mọi dependency hữu ích cần được khai báo trong `requirements.txt`.

## Shortcuts

Kích hoạt môi trường venv (Windows):

```sh
.venv\Scripts\activate
```

Tải dependencies:

```sh
pip install -r requirements.txt
```

Nên kích hoạt venv và chỉ làm việc trong môi trường venv.
