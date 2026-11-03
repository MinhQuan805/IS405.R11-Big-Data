# Dynamic Percentile-Equilibrated University Admission Framework
> **Khung mô hình ước lượng xác suất trúng tuyển đại học dựa trên phân vị cân bằng động trên nền tảng dữ liệu lớn (Big Data & MLOps)**

---

## 1. Giới Thiệu Dự Án

Dự án cung cấp một framework phân tích dữ liệu lớn và học máy xác suất nhằm giải quyết bài toán: **Ước lượng xác suất trúng tuyển liên tục $P(\text{Trúng tuyển}_{i, j, t}) = \mathbb{P}(S_{i, k, t} \ge C_{j, k, t})$** của thí sinh $i$ vào ngành $j$, tổ hợp $k$ tại năm tuyển sinh $t$.

Hệ thống được thiết kế theo kiến trúc **Mềm dẻo (Engine-Agnostic & Decoupled Architecture)** dựa trên mẫu **Ports & Adapters (Hexagonal Architecture)**:
- **Độc lập nền tảng tính toán:** Cho phép người dùng chuyển đổi linh hoạt giữa máy đơn (Python thuần, Pandas, DuckDB) và cụm dữ liệu lớn phân tán (Apache Spark, Hadoop) chỉ bằng 1 dòng cấu hình.
- **Cơ chế "Hộp đen / Túi mù" (Inversion of Control - IoC):** Người dùng có thể cắm công nghệ hoặc script riêng của mình vào hệ thống mà không cần hiểu cú pháp nội bộ của framework.
- **Tách rời Model Serving:** Dịch vụ suy luận trực tuyến phục vụ người dùng qua REST API hoạt động độc lập, đạt độ trễ siêu tốc $\approx 7\text{ms}$/request.

Tài liệu chi tiết liên quan:
- [Đặc tả bài toán & Mô hình toán 4 thành phần](docs/problem-specification.md)
- [Hợp đồng dữ liệu & Ràng buộc Schema](docs/data-contract.md)
- [Kế hoạch triển khai Big Data & Hướng dẫn MLOps](docs/big-data-processing-implement-plan.md)

---

## 2. Cấu Trúc Dự Án

```text
IS405.R11-Big-Data/
├── src/admission_core/              # LÕI FRAMEWORK CHUẨN MLOPS (Cài đặt qua pip install -e .)
│   ├── specs/                       # Quy định của Framework (The WHAT)
│   │   ├── contracts.py             # 16 đặc trưng chính thức, target R*, tiêu chuẩn Data Contract
│   │   └── math_formulas.py         # Công thức giải tích Module 4, hàm sống sót 1-F(s)
│   ├── ports/                       # Cổng giao diện trừu tượng (BaseCDFPort, BaseTrainerPort,...)
│   ├── backends/                    # Bộ chuyển đổi tính toán mặc định (Local Pandas/DuckDB)
│   ├── validation/                  # Cổng kiểm định chất lượng tự động (Quality Gate vs Sàn Bayes)
│   ├── reporting/                   # Xuất báo cáo markdown tự động
│   ├── factory.py                   # BỘ ĐIỀU PHỐI IoC (Dynamic Plugin & Script Loader)
│   ├── pipeline.py                  # "TÚI MÙ" ORCHESTRATOR (Tự động Retry, Fallback, Rollback)
│   ├── cli.py & __main__.py         # Giao diện dòng lệnh hợp nhất: python -m admission_core
│
├── plugins/                         # NƠI USER IMPLEMENT CÔNG NGHỆ RIÊNG
│   ├── custom_cdf_adapter.py        # [Cấp 2: Class Adapter] User implement qua hàm execute()
│   └── custom_script_cdf.py         # [Cấp 1: Script Độc Lập] Standalone script ZERO-FRAMEWORK syntax
│
├── config/                          # Quản trị cấu hình hệ thống
│   ├── pipeline_config.yaml         # Tệp cấu hình điều khiển động toàn bộ pipeline
│   └── dirs.yaml                    # Danh mục đường dẫn (tương thích ngược)
│
├── serving/                         # DỊCH VỤ SUY LUẬN TRỰC TUYẾN (Decoupled Model Hosting)
│   └── app.py                       # RESTful Inference Server độc lập (~7ms/request)
│
├── models/                          # Lưu trữ Artifact mô hình chính thức & metadata
│   ├── best_lightgbm_regressor.joblib
│   ├── lightgbm_quantile_0.1.joblib
│   ├── lightgbm_quantile_0.5.joblib
│   ├── lightgbm_quantile_0.9.joblib
│   └── model_metadata.json
│
├── reports/                         # Báo cáo đánh giá mô hình tự động sinh ra sau khi chạy
│   └── evaluation_summary.md
│
├── data-raw/                        # Dữ liệu thô (Bronze Layer: điểm thi 10M+ dòng, trends)
├── data-cleaned/                    # Dữ liệu chuẩn hóa Parquet (Silver/Gold Layer)
├── docs/                            # Tài liệu đặc tả kỹ thuật và hợp đồng dữ liệu
├── helpers/                         # Script phụ trợ convert Parquet và crawl dữ liệu
├── scripts-fetching/                # Sandbox notebook và unit-script thu thập dữ liệu
├── scripts-processing/              # Sandbox notebook và unit-script làm sạch dữ liệu
├── pyproject.toml                   # Định nghĩa package chuẩn Python
└── requirements.txt                 # Danh mục thư viện phụ thuộc
```

---

## 3. Cài Đặt Môi Trường

Khuyến nghị sử dụng Python 3.9 - 3.11 trong môi trường ảo:

### 3.1 Kích hoạt Virtual Environment (Windows)
```powershell
.venv\Scripts\activate
```
*(Trên Linux/macOS: `source .venv/bin/activate`)*

### 3.2 Cài đặt Dependencies & Cài đặt Package lõi
```powershell
# Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# Cài đặt lõi framework admission-core ở chế độ editable
pip install -e . --no-deps
```

---

## 4. Hướng Dẫn Sử Dụng (Usage Guide)

Toàn bộ hệ thống được điều khiển thống nhất qua CLI `python -m admission_core`:

### 4.1 Khởi chạy toàn bộ quy trình tự động hóa ("Túi Mù" End-to-End)
Chạy toàn bộ pipeline từ nạp dữ liệu $\to$ tính CDF $\to$ trích xuất đặc trưng đa tầng $\to$ huấn luyện LightGBM $\to$ kiểm định sàn Bayes $\to$ xuất báo cáo:

```powershell
python -m admission_core run --config config/pipeline_config.yaml
```

**Đầu ra sau khi chạy:**
- Mô hình cập nhật tại: `models/best_lightgbm_regressor.joblib`
- Báo cáo chất lượng tại: `reports/evaluation_summary.md` (RMSE $\approx 0.14$, $R^2 \approx 0.83$)

---

### 4.2 Chạy thử nghiệm riêng từng công đoạn (Dry-Run Stages)
Hữu ích khi bạn muốn kiểm tra riêng công nghệ của mình:

```powershell
# Chỉ chạy riêng công đoạn tính CDF
python -m admission_core run-stage --stage cdf --config config/pipeline_config.yaml

# Chỉ chạy riêng công đoạn trích xuất đặc trưng
python -m admission_core run-stage --stage features --config config/pipeline_config.yaml
```

---

### 4.3 Khởi chạy Model Serving API Server (Internet-Facing)
Khởi chạy dịch vụ API thời gian thực độc lập phục vụ ứng dụng web/mobile:

```powershell
python -m admission_core serve --host 127.0.0.1 --port 8000
```

**Các Endpoint phục vụ:**
1. **Kiểm tra trạng thái (Health Check):**
   ```text
   GET http://127.0.0.1:8000/api/v2/health
   ```
2. **Thông tin mô hình hiện hành (Metadata):**
   ```text
   GET http://127.0.0.1:8000/api/v2/models/current-metadata
   ```
3. **Dự đoán xác suất trúng tuyển:**
   ```text
   POST http://127.0.0.1:8000/api/v2/predict/admission-probability
   Content-Type: application/json

   {
     "student_id": "TS2025_001928",
     "score_year": 2025,
     "school_id": "BKA",
     "score_code": "IT1",
     "score_blocks": "A00",
     "total_score": 26.5
   }
   ```
   *Response mẫu:*
   ```json
   {
     "status": "success",
     "student_percentile": {
       "block": "A00",
       "calculated_rank_pct": 0.0245,
       "rank_interpretation": "Thí sinh nằm trong Top 2.45% toàn quốc"
     },
     "admission_probability": {
       "probability_value": 0.7285,
       "probability_percentage": "72.85%",
       "decision_tier": "Cạnh tranh (Competitive)",
       "recommendation_guidance": "Điểm của thí sinh sát ngưỡng trung vị. Khả năng đỗ khả quan nhưng chịu rủi ro lọc ảo; cần lót thêm nguyện vọng an toàn."
     },
     "inference_latency_ms": 7.0
   }
   ```

---

## 5. Hướng Dẫn Cắm Rút Công Nghệ Của Người Dùng (Plugin Guide)

Framework cho phép bạn đưa công nghệ xử lý của mình (Spark, Polars, DuckDB, Shell script...) vào thay thế mà **không cần sửa code framework**:

### Cách 1: Script độc lập (Zero-Framework Syntax - Tiện nhất)
Viết một script Python/Shell nhận `--input` và `--output` qua `argparse` (ví dụ: `plugins/custom_script_cdf.py`), không cần import framework.

Khai báo trong `config/pipeline_config.yaml`:
```yaml
backend_execution:
  cdf_stage:
    type: "external_script"
    command: "python plugins/custom_script_cdf.py --input {input_uri} --output {output_uri}"
```

### Cách 2: Class Adapter Plugin
Tạo một class triển khai hàm `execute(input_uri, output_uri)` (ví dụ: `plugins/custom_cdf_adapter.py`).

Khai báo trong `config/pipeline_config.yaml`:
```yaml
backend_execution:
  cdf_stage:
    type: "class_adapter"
    target: "plugins.custom_cdf_adapter.CustomUserCDFAdapter"
```

Khi chạy lại `python -m admission_core run`, framework sẽ tự động kích hoạt mã nguồn của bạn.

---

## 6. Tiêu Chuẩn & Quy Tắc Phát Triển

- **Mã hóa:** Luôn mã hóa `UTF-8` khi đọc/ghi file.
- **Định dạng dữ liệu:** Mọi dữ liệu phân tích đều lưu trữ ở định dạng chuẩn **Parquet** (nén Snappy). Sử dụng script hỗ trợ nếu cần:
  ```powershell
  python helpers/convert_to_parquet.py data-cleaned
  ```
- **Hợp đồng dữ liệu:** Mọi đặc trưng đầu vào/ra của các module phải tuân thủ nghiêm ngặt theo [Data Contract](docs/data-contract.md).
- **Kiểm định chất lượng:** Mọi lần cập nhật mô hình tự động đều được kiểm định qua Sàn Sai số Bayes ($\text{MSE} \approx 0.02283$). Mô hình không đạt chuẩn sẽ tự động bị Rollback.
