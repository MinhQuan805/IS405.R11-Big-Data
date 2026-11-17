# Dynamic Percentile-Equilibrated University Admission Framework
> **Khung mô hình ước lượng xác suất trúng tuyển đại học dựa trên phân vị cân bằng động trên nền tảng dữ liệu lớn (Big Data & MLOps)**

Hướng dẫn chạy và giải thích chi tiết thuật toán Contract 3.0, PySpark 4.3.0 và Model Serving nằm trong [Đặc tả Kỹ thuật Pipeline Dữ liệu Lớn](docs/big-data-pipeline-specification.md). Kết quả kiểm chứng được ghi tại [Kết quả triển khai](reports/implementation_verification.md).

Phiên bản hiện tại sử dụng 15 đặc trưng, kiểm định theo năm, CDF thực nghiệm và API gọi mô hình thực. Mô hình dùng contract cũ cần được huấn luyện lại. Dữ liệu thực đã được nhập trong `data/`. Chuẩn bị điểm chuẩn bằng `python scripts/prepare_real_data.py` trước khi chạy cấu hình mặc định. Kết quả dữ liệu thực nằm trong [Kết quả xử lý dữ liệu tuyển sinh](reports/real_data_results.md). Có thể tạo dữ liệu kiểm chứng bằng `python -m admission_core.demo --output runs/demo`.

---

## 1. Giới Thiệu Dự Án

Dự án cung cấp một framework phân tích dữ liệu lớn và học máy xác suất nhằm giải quyết bài toán: **Ước lượng xác suất trúng tuyển liên tục $P(\text{Trúng tuyển}_{i, j, t}) = \mathbb{P}(S_{i, k, t} \ge C_{j, k, t})$** của thí sinh $i$ vào ngành $j$, tổ hợp $k$ tại năm tuyển sinh $t$.

Hệ thống được thiết kế theo kiến trúc **Mềm dẻo (Engine-Agnostic & Decoupled Architecture)** dựa trên mẫu **Ports & Adapters (Hexagonal Architecture)**:
- **Nền tảng tính toán:** Hai backend đã triển khai là `local_pandas` và `apache_spark`. Spark thực hiện CDF và tạo đặc trưng. LightGBM huấn luyện trên bảng Gold cục bộ.
- **Cơ chế "Hộp đen / Túi mù" (Inversion of Control - IoC):** Người dùng có thể cắm công nghệ hoặc script riêng của mình vào hệ thống mà không cần hiểu cú pháp nội bộ của framework.
- **Model Serving:** Dịch vụ REST API nạp một phiên bản mô hình cùng CDF và feature lookup. Độ trễ phụ thuộc môi trường và cần được đo trên workload cụ thể.

Tài liệu chi tiết liên quan trong thư mục `docs/`:
- [Đặc tả Kỹ thuật & Hướng dẫn Pipeline Dữ liệu Lớn](docs/big-data-pipeline-specification.md) — *Kiến trúc Spark 4.3.0, 15 đặc trưng Contract 3.0, tiền xử lý dữ liệu thực và Model Serving.*
- [Đặc tả bài toán & Mô hình toán 4 thành phần](docs/problem-specification.md)
- [Hợp đồng dữ liệu & Ràng buộc Schema](docs/data-contract.md)
- [Kế hoạch triển khai Big Data & Hướng dẫn MLOps](docs/big-data-processing-implement-plan.md)

---

## 2. Cấu Trúc Dự Án

```text
IS405.R11-Big-Data/
├── src/admission_core/              # Package lõi, cài đặt bằng pip install .
│   ├── specs/                       # Quy định của Framework (The WHAT)
│   │   ├── contracts.py             # 15 đặc trưng, target R*, contract 3.0
│   │   └── math_formulas.py         # Công thức giải tích Module 4, hàm sống sót 1-F(s)
│   ├── ports/                       # Cổng giao diện trừu tượng (BaseCDFPort, BaseTrainerPort,...)
│   ├── backends/                    # local_pandas và apache_spark
│   ├── validation/                  # Kiểm định metric ngoài mẫu theo năm
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
│   └── app.py                       # Entry point của dịch vụ suy luận HTTP
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

Sử dụng Python từ 3.11 và môi trường Java tương thích với Spark. Hướng dẫn cấu hình Windows được trình bày trong `docs/big-data-pipeline-specification.md`.

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
pip install '.[spark,dev]'
```

---

## 4. Hướng Dẫn Sử Dụng (Usage Guide)

Toàn bộ hệ thống được điều khiển thống nhất qua CLI `python -m admission_core`:

### 4.1 Khởi chạy toàn bộ quy trình tự động hóa ("Túi Mù" End-to-End)
Chạy pipeline từ nạp dữ liệu $\to$ tính CDF $\to$ tạo đặc trưng $\to$ huấn luyện LightGBM $\to$ kiểm định theo năm $\to$ xuất báo cáo và phát hành phiên bản model:

```powershell
python -m admission_core run --config config/pipeline_config.yaml
```

**Đầu ra sau khi chạy:**
- Mô hình được ghi vào `models/versions/<run_id>/`, bản hiện hành được xác định bằng `models/current.json`.
- Báo cáo chất lượng được ghi theo `data_paths.report_output`. Các chỉ số được tính lại bằng kiểm định theo năm khi chạy pipeline.

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
- **Kiểm định chất lượng:** Model ứng viên phải đạt các ngưỡng cấu hình trước khi được phát hành. Khi thất bại, tham chiếu phiên bản đang phục vụ được giữ nguyên. Điều kiện so sánh với hằng số sai số tham chiếu cũ được tắt trong cấu hình mặc định.
