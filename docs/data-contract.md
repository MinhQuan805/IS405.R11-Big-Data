# Data Contract — Đặc Tả Hợp Đồng Dữ Liệu Dự Án IS405.R11 Big Data

**Mục đích của tài liệu này**: Đặc tả cấu trúc schema, kiểu dữ liệu theo chuẩn pandas, trạng thái sử dụng, ý nghĩa nghiệp vụ, quy trình làm sạch và các ràng buộc toàn vẹn dữ liệu cho toàn bộ các tập dữ liệu thô (_Raw Data_) và dữ liệu đã làm sạch (_Cleaned Data_) phục vụ phân tích đặc trưng và xây dựng mô hình dự đoán điểm chuẩn tuyển sinh đại học kết hợp xu hướng tìm kiếm Google Trends.

---

## Tổng quan Kiến trúc Luồng Dữ liệu (Data Flow)

Dự án tổ chức dữ liệu thành 3 nhánh chính được cấu hình đường dẫn tại `config/dirs.yaml`:

- **Nhánh Điểm chuẩn Tuyển sinh:** Thu thập từ cổng thông tin tuyển sinh trực tuyến, trải qua tiền xử lý bởi các script trong `scripts-processing/unit-scripts/` (xuất từ `scripts-processing/notebooks/`).
- **Nhánh Google Trends:** Thu thập bán tự động qua Google Knowledge Graph & Trends API bởi `scripts-fetching/unit-scripts/get_trends.py`, lưu trữ bộ đệm SQLite3 và JSON tổng hợp, sau đó được phẳng hóa (flatten & normalize) thành 6 bảng quan hệ CSV chuyên biệt qua `scripts-processing/unit-scripts/clean_trends.py`.
- **Nhánh Phổ điểm Thi Tốt nghiệp THPT (Score Distributions):** Thu thập dữ liệu điểm thi toàn quốc của từng thí sinh theo kỳ thi tốt nghiệp THPT qua các năm (gồm Chương trình 2006 từ 2016–2025 và Chương trình 2018 mới từ 2025). Dữ liệu này được lưu trữ nguyên bản tại `data-raw/score-distribution/` và **được sử dụng trực tiếp** để tính toán hàm phân phối tích lũy CDF ($F_{k, t}$) và thứ hạng phân vị ($R^*_{j, t}$), không cần quy trình làm sạch (cleaned).

Các tệp dữ liệu điểm chuẩn và Google Trends tồn tại ở cả 2 trạng thái **Raw** và **Cleaned** được gộp chung vào bảng đối chiếu. Riêng dữ liệu phổ điểm là dữ liệu chuẩn hóa của Bộ GD&ĐT được sử dụng trực tiếp ở trạng thái thô.

```
[data-raw/admission-cutoff-score/] ───> [cutoff_scores.py, majors.py, score_blocks.py] ───> [data-cleaned/admission-cutoff-score/]
[data-raw/google-trends/]           ───> [clean_trends.py]                             ───> [data-cleaned/google-trends/]
[data-raw/score-distribution/]      ─────────────────── (Sử dụng trực tiếp) ─────────────> [Tính toán CDF & Phân vị điểm chuẩn]
```

---

## Dữ liệu Điểm chuẩn Tuyển sinh (Admission Cutoff Scores)

### Tập dữ liệu Điểm chuẩn Tuyển sinh (`cutoff-scores.csv`)

- **Tệp thô (Raw):** `data-raw/admission-cutoff-score/cutoff-scores.csv` — 147,671 dòng, 15 cột.
- **Tệp sạch (Cleaned):** `data-cleaned/admission-cutoff-score/cutoff-scores.csv` — 101,466 dòng, 13 cột (giảm 46,205 dòng sau tiền xử lý).
- **Mô tả:** Dữ liệu điểm chuẩn tuyển sinh đại học/cao đẳng công bố qua các năm. Tập cleaned đã được lọc phạm vi nghiên cứu 2010–2025, quy đổi thang điểm 40 về thang 30, chuẩn hóa danh mục tổ hợp/mã ngành và loại ngoại lai IQR.
- **Khóa chính tiềm năng:** Bộ khóa tự nhiên `(school_id, score_code, score_year, score_admission_name, score_blocks)`.
- **Script xử lý tương ứng:** `scripts-processing/notebooks/cutoff-scores.ipynb` / `scripts-processing/unit-scripts/cutoff_scores.py`.

| STT | Tên thuộc tính             | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                                        | Phương pháp làm sạch (nếu có)                                                                                                                                                                               | Ghi chú (nếu có)                                                                                                  |
| :-: | :------------------------- | :-------------------: | :----------: | :----------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------- |
|  1  | `school_id`                |       `object`        |    **Có**    | Mã định danh trường ĐH/CĐ do BGD quy định (VD: NEU, BKA, CDD0209)        | Loại bỏ khoảng trắng thừa đầu cuối (`strip()`)                                                                                                                                                              | 302 trường duy nhất ở cleaned, 0 null.                                                                            |
|  2  | `school_name`              |       `object`        |    **Có**    | Tên đầy đủ của trường ĐH/CĐ                                              | Loại bỏ ký tự xuống dòng `\r`, `\n` (`remove_newlines`), strip khoảng trắng                                                                                                                                 | Tiếng Việt có dấu, 0 null.                                                                                        |
|  3  | `school_type`              |       `object`        |    **Có**    | Cấp bậc đào tạo của cơ sở giáo dục ('Đại học', 'Cao đẳng')               | Chuẩn hóa ký tự xuống dòng (`remove_newlines`)                                                                                                                                                              | Gồm 2 giá trị phân loại, 0 null.                                                                                  |
|  4  | `school_short_name`        |       `object`        |    **Có**    | Tên viết tắt thông dụng của trường (VD: HUST, NEU, FTU)                  | Chuẩn hóa ký tự xuống dòng (`remove_newlines`)                                                                                                                                                              | Raw có 9,106 null (6.2%); Cleaned còn 2,905 null (2.9%).                                                          |
|  5  | `province_id`              |        `int64`        |    **Có**    | Mã định danh số của tỉnh/thành phố nơi trường đặt trụ sở chính           | Lọc bỏ các dòng bị khuyết thiếu (`dropna`)                                                                                                                                                                  | Gồm 33 mã tỉnh ở raw, 30 mã ở cleaned (mã tỉnh do dataset tự quy định).                                           |
|  6  | `province_name`            |       `object`        |    **Có**    | Tên tỉnh/thành phố nơi trường đặt trụ sở chính                           | Chuẩn hóa chuỗi (`remove_newlines`), `dropna`                                                                                                                                                               | Khớp 1-1 với `province_id`, 0 null.                                                                               |
|  7  | `score_code`               |       `object`        |    **Có**    | Mã ngành / chuyên ngành tuyển sinh theo đề án của trường                 | `dropna()`, sau đó đối soát `is_valid_score_code()` chỉ giữ các mã có trong `majors.csv`                                                                                                                    | 2,564 mã ngành hợp lệ ở cleaned, 0 null.                                                                          |
|  8  | `score_name`               |       `object`        |    **Có**    | Tên ngành / chuyên ngành / chương trình đào tạo tuyển sinh               | Chuẩn hóa chuỗi (`remove_newlines`), `dropna()`                                                                                                                                                             | 0 null ở cleaned.                                                                                                 |
|  9  | `score_blocks`             |       `object`        |    **Có**    | Danh sách các tổ hợp môn xét tuyển áp dụng cho ngành                     | Đổi dấu phẩy `,` thành dấu chấm phẩy `;`, xóa khoảng trắng thừa (`\s+`), lọc đối chiếu chỉ giữ các mã có trong `score-blocks.csv`                                                                           | Raw phân cách bằng dấu phẩy; Cleaned phân cách bằng dấu chấm phẩy (còn 32,468 null, 32.0%).                       |
| 10  | `score_mark`               |       `float64`       |    **Có**    | Điểm chuẩn trúng tuyển công bố (biến mục tiêu dự đoán)                   | (1) `dropna()`; (2) Nhận diện từ khóa thang 40 (`'thang 40'`, `'he so 2'`...) trong `score_introtext` để quy đổi về thang 30: `score_mark / 40 * 30`; (3) Lọc ngoại lai IQR theo từng phương thức xét tuyển | Biến mục tiêu. Chú ý: code gốc lọc nhầm `score_year > 0` thay vì `score_mark > 0` nên vẫn còn 1,313 dòng $\le 0$. |
| 11  | `score_year`               |        `int64`        |    **Có**    | Năm tuyển sinh tương ứng với mức điểm chuẩn                              | Ép kiểu về `int64` (ở raw là `float64`), lọc phạm vi nghiên cứu $2010 \le \text{year} \le 2025$                                                                                                             | 16 năm liên tục (2010–2025), 0 null ở cleaned (raw có 4,212 null).                                                |
| 12  | `score_introtext`          |       `object`        |    **Có**    | Ghi chú văn bản tự do về tiêu chí phụ, quy tắc tính điểm, môn nhân hệ số | Chuẩn hóa ký tự xuống dòng (`remove_newlines`)                                                                                                                                                              | Dùng để dò tìm quy đổi thang 40. Tỷ lệ rỗng cao: Raw 77.3% null, Cleaned 79.7% null.                              |
| 13  | `score_formula`            |       `object`        |  **Không**   | Công thức tính điểm xét tuyển (VD: `MON_1+MON_2+MON_3+UT`)               | Bị loại bỏ hoàn toàn, vì dữ liệu này thực tế không có giá trị sử dụng                                                                                                                                       | Bị loại bỏ khỏi `data-cleaned/` (raw có 115,649 null, 78.3%).                                                     |
| 14  | `score_is_converted_score` |       `float64`       |  **Không**   | Cờ nhị phân biểu thị điểm đã qua quy đổi hay chưa (1.0 hoặc 0.0)         | Bị loại bỏ hoàn toàn, vì dữ liệu này thực tế không có giá trị sử dụng                                                                                                                                       | Bị loại bỏ khỏi `data-cleaned/` (raw có 158 null, 0.1%).                                                          |
| 15  | `score_admission_name`     |       `object`        |    **Có**    | Tên phương thức xét tuyển (VD: 'Điểm thi THPT', 'Điểm học bạ'...)        | `dropna()`, ánh xạ từ điển `mapping` để sửa triệt để các chuỗi lỗi font/UTF-8 hỏng thành 13 tên chuẩn                                                                                                       | Raw bị lỗi font nhiều ký tự lạ (158 null); Cleaned chuẩn hóa thành 13 phương thức, 0 null.                        |

---

### Tập dữ liệu Danh mục Ngành & Nhóm ngành (`majors.csv`)

- **Tệp thô (Raw):** `data-raw/admission-cutoff-score/majors.csv` — 506 dòng, 6 cột.
- **Tệp sạch (Cleaned):** `data-cleaned/admission-cutoff-score/majors.csv` — 506 dòng, 6 cột.
- **Mô tả:** Danh mục chuẩn quốc gia về phân cấp nhóm ngành và ngành đào tạo đại học kèm danh sách mã tuyển sinh thực tế tương ứng.
- **Khóa chính:** `major_id`.
- **Script xử lý tương ứng:** `scripts-processing/notebooks/majors.ipynb` / `scripts-processing/unit-scripts/majors.py`.

| STT | Tên thuộc tính      | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                                    | Phương pháp làm sạch (nếu có)                                                  | Ghi chú (nếu có)                                                                |
| :-: | :------------------ | :-------------------: | :----------: | :------------------------------------------------------------------- | :----------------------------------------------------------------------------- | :------------------------------------------------------------------------------ |
|  1  | `major_group_id`    |        `int64`        |    **Có**    | Mã định danh nhóm ngành cấp 1                                        | Giữ nguyên kiểu dữ liệu số nguyên                                              | 37 nhóm ngành, 0 null.                                                          |
|  2  | `major_group_name`  |       `object`        |    **Có**    | Tên nhóm ngành cấp 1 (VD: 'Máy tính - CNTT', 'Kinh doanh')           | Áp dụng `remove_newlines` loại bỏ ký tự `\r`, `\n` và strip khoảng trắng thừa  | 37 tên nhóm, 0 null.                                                            |
|  3  | `major_id`          |        `int64`        |    **Có**    | Mã định danh ngành đào tạo cấp 2                                     | Giữ nguyên kiểu dữ liệu số nguyên                                              | Khóa chính cấp ngành, 452 mã duy nhất, 0 null.                                  |
|  4  | `major_name`        |       `object`        |    **Có**    | Tên chuẩn ngành đào tạo cấp 2                                        | Áp dụng `remove_newlines`, strip khoảng trắng thừa                             | 451 tên ngành, 0 null.                                                          |
|  5  | `major_description` |       `object`        |    **Có**    | Mô tả chi tiết ngành đào tạo hoặc danh sách chuyên ngành đào tạo hẹp | Áp dụng `remove_newlines`, strip khoảng trắng thừa                             | Còn 22 giá trị null (4.3%).                                                     |
|  6  | `score_codes`       |       `object`        |    **Có**    | Danh sách các mã ngành tuyển sinh thực tế tương ứng                  | Đổi dấu phẩy `,` thành dấu chấm phẩy `;`, loại bỏ toàn bộ khoảng trắng (`\s+`) | Dùng làm tập khóa ngoại kiểm tra tính hợp lệ cho `score_code` trong điểm chuẩn. |

---

### Tập dữ liệu Danh mục Tổ hợp Môn (`score-blocks.csv`)

- **Tệp thô (Raw):** `data-raw/admission-cutoff-score/score-blocks.csv` — 280 dòng, 5 cột.
- **Tệp sạch (Cleaned):** `data-cleaned/admission-cutoff-score/score-blocks.csv` — 280 dòng, 5 cột.
- **Mô tả:** Danh mục các tổ hợp môn xét tuyển đại học truyền thống và hiện đại (khối A00, A01, B00, C00, D01...) kèm các môn thi thành phần đã chuẩn hóa chính tả.
- **Khóa chính:** `code`.
- **Script xử lý tương ứng:** `scripts-processing/notebooks/score-blocks.ipynb` / `scripts-processing/unit-scripts/score_blocks.py`.

| STT | Tên thuộc tính | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                   | Phương pháp làm sạch (nếu có)                                                                                                                                                                                                                                                                                                                                      | Ghi chú (nếu có)                                                     |
| :-: | :------------- | :-------------------: | :----------: | :-------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------- |
|  1  | `code`         |       `object`        |    **Có**    | Mã ký hiệu tổ hợp môn xét tuyển (VD: A00, D01, C01) | Giữ nguyên ký tự mã                                                                                                                                                                                                                                                                                                                                                | Khóa chính danh mục tổ hợp, 279 mã duy nhất, 0 null.                 |
|  2  | `subject1`     |       `object`        |    **Có**    | Tên môn thi thành phần thứ nhất trong tổ hợp        | Đồng nhất Unicode NFC, gom khoảng trắng, thay 'lý' $\rightarrow$ 'lí', sửa dấu thanh, chuẩn hóa viết hoa ngoại ngữ, ánh xạ tên rút gọn (`gdktpl` $\rightarrow$ `gdkt&pl`, `hóa` $\rightarrow$ `hóa học`, `lí` $\rightarrow$ `vật lí`, `địa` $\rightarrow$ `địa lí`, `tin` $\rightarrow$ `tin học`, `sinh` $\rightarrow$ `sinh học`, `văn` $\rightarrow$ `ngữ văn`) | 0 null (VD: 'Toán', 'Ngữ văn').                                      |
|  3  | `subject2`     |       `object`        |    **Có**    | Tên môn thi thành phần thứ hai trong tổ hợp         | Đồng nhất Unicode NFC, gom khoảng trắng, thay 'lý' $\rightarrow$ 'lí', sửa dấu thanh, chuẩn hóa viết hoa ngoại ngữ, ánh xạ tên rút gọn (`gdktpl` $\rightarrow$ `gdkt&pl`, `hóa` $\rightarrow$ `hóa học`, `lí` $\rightarrow$ `vật lí`, `địa` $\rightarrow$ `địa lí`, `tin` $\rightarrow$ `tin học`, `sinh` $\rightarrow$ `sinh học`, `văn` $\rightarrow$ `ngữ văn`) | 0 null (VD: 'Vật lí', 'Hóa học').                                    |
|  4  | `subject3`     |       `object`        |    **Có**    | Tên môn thi thành phần thứ ba trong tổ hợp          | Đồng nhất Unicode NFC, gom khoảng trắng, thay 'lý' $\rightarrow$ 'lí', sửa dấu thanh, chuẩn hóa viết hoa ngoại ngữ, ánh xạ tên rút gọn (`gdktpl` $\rightarrow$ `gdkt&pl`, `hóa` $\rightarrow$ `hóa học`, `lí` $\rightarrow$ `vật lí`, `địa` $\rightarrow$ `địa lí`, `tin` $\rightarrow$ `tin học`, `sinh` $\rightarrow$ `sinh học`, `văn` $\rightarrow$ `ngữ văn`) | 0 null (VD: 'Tiếng Anh', 'Sinh học').                                |
|  5  | `subject4`     |       `object`        |    **Có**    | Tên môn thi thành phần thứ tư hoặc môn năng khiếu   | Áp dụng cùng hàm chuẩn hóa `normalize_text()`                                                                                                                                                                                                                                                                                                                      | Có 279 giá trị null (99.6%), chỉ duy nhất 1 dòng có giá trị ('Hát'). |

---

## Dữ liệu Xu hướng Tìm kiếm (Google Trends)

### Tập dữ liệu Danh mục Chủ đề Từ khóa (`trend_topics.csv`)

- **Tệp thô (Raw):** `data-raw/google-trends/trend_topics.csv` — 3,579 dòng, 5 cột.
- **Tệp sạch (Cleaned):** `data-cleaned/google-trends/trend_topics.csv` — 3,579 dòng, 5 cột.
- **Mô tả:** Danh mục các từ khóa thực thể tuyển sinh tiếng Việt ban đầu kèm danh sách các Topic MID ứng viên gợi ý từ Google Knowledge Graph API.
- **Khóa liên kết:** `(keyword, keyword_type, mid, title)`.
- **Script xử lý tương ứng:** `scripts-fetching/unit-scripts/get_topics.py` (tạo raw) / `scripts-processing/unit-scripts/clean_trends.py` (làm sạch).

| STT | Tên thuộc tính | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                                         | Phương pháp làm sạch (nếu có)                                    | Ghi chú (nếu có)                                                                              |
| :-: | :------------- | :-------------------: | :----------: | :------------------------------------------------------------------------ | :--------------------------------------------------------------- | :-------------------------------------------------------------------------------------------- |
|  1  | `keyword`      |       `object`        |    **Có**    | Tên thực thể tuyển sinh tiếng Việt ban đầu đưa vào tìm kiếm topic         | Áp dụng `clean_str()` (xóa khoảng trắng thừa), lọc bỏ chuỗi rỗng | 921 từ khóa duy nhất, 0 null.                                                                 |
|  2  | `keyword_type` |       `object`        |    **Có**    | Phân loại ngữ nghĩa của từ khóa tuyển sinh (6 loại)                       | `clean_str()`, chuẩn hóa chuỗi                                   | Gồm 6 loại: `school`, `major`, `major_group`, `subject`, `subject_group`, `admission_method`. |
|  3  | `mid`          |       `object`        |    **Có**    | Mã Machine ID (MID) của chủ đề Google Knowledge Graph (VD: `/g/122jr9l6`) | `clean_str()`, strip khoảng trắng                                | 2,683 MID ứng viên khác nhau.                                                                 |
|  4  | `title`        |       `object`        |    **Có**    | Tiêu đề hiển thị của chủ đề đại diện từ Google                            | `clean_str()`                                                    | 2,584 tiêu đề duy nhất.                                                                       |
|  5  | `type`         |       `object`        |    **Có**    | Mô tả loại thực thể từ Knowledge Graph (VD: 'Trường cao đẳng', 'Chủ đề')  | `clean_str()`, chuyển null thành chuỗi rỗng `""`                 | Khử trùng lặp `drop_duplicates(subset=['keyword', 'keyword_type', 'mid', 'title'])`.          |

---

### File Raw: Dữ liệu Tổng hợp Phân cấp (`trends.json`)

- **Đường dẫn tệp:** `data-raw/google-trends/trends.json`
- **Kích thước:** 879 phần tử JSON (dung lượng ~23.7 MB).
- **Mô tả:** Tệp JSON lồng cấp chứa toàn bộ kết quả crawl từ Google Trends API (timeline tháng, phân bổ tỉnh thành, truy vấn liên quan Top/Rising, metadata chấm điểm topic và log trạng thái crawl).
- **Khóa chính cấp phần tử:** `query_id`.
- **Script xử lý tương ứng:** `scripts-fetching/unit-scripts/get_trends.py` (tạo file) $\rightarrow$ `scripts-processing/unit-scripts/clean_trends.py` (phẳng hóa thành 6 bảng quan hệ).

| STT | Tên thuộc tính              | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                                                        | Phương pháp làm sạch (nếu có)                                                   | Ghi chú (nếu có)                                                |
| :-: | :-------------------------- | :-------------------: | :----------: | :--------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------ | :-------------------------------------------------------------- |
|  1  | `query_id`                  |       `object`        |    **Có**    | Mã băm định danh duy nhất (20 ký tự hex) cho query Trends                                | Sinh tự động bằng hàm băm MD5/SHA256 của chuỗi query                            | Khóa chính của mỗi record trong mảng JSON.                      |
|  2  | `query`                     |       `object`        |    **Có**    | Chuỗi query thực tế gửi tới Google Trends (MID hoặc keyword)                             | Dữ liệu thô từ pipeline fetching                                                | 559 Topic MID và 320 search term fallback.                      |
|  3  | `query_kind`                |       `object`        |    **Có**    | Phân loại loại truy vấn ('topic_mid' hoặc 'search_term')                                 | Xác định tự động theo kết quả chấm điểm topic                                   | 2 giá trị duy nhất.                                             |
|  4  | `mid`                       |       `object`        |    **Có**    | Mã Topic MID tương ứng                                                                   | Ghi nhận nếu `query_kind == 'topic_mid'`                                        | Null/rỗng nếu là search_term.                                   |
|  5  | `keyword_metadata`          |    `object` (list)    |    **Có**    | Danh sách chi tiết các thực thể gộp chung vào query kèm độ liên quan                     | Mảng dict chứa `keyword`, `keyword_type`, `relevance_score`, `selection_reason` | Được phẳng hóa thành bảng `trend_keywords.csv`.                 |
|  6  | `title`                     |       `object`        |    **Có**    | Tiêu đề hiển thị của chủ đề Google Trends                                                | Dữ liệu thô từ API                                                              | Rỗng nếu là search term.                                        |
|  7  | `type`                      |       `object`        |    **Có**    | Loại thực thể từ Google Knowledge Graph                                                  | Dữ liệu thô từ API                                                              | Rỗng nếu là search term.                                        |
|  8  | `selection_score`           |       `float64`       |    **Có**    | Điểm số lựa chọn/độ liên quan của topic [0.0, 1.0]                                       | Tính bởi thuật toán lọc topic của fetching pipeline                             | Đánh giá độ khớp ngữ nghĩa.                                     |
|  9  | `status`                    |       `object`        |    **Có**    | Trạng thái thu thập tổng thể ('success', 'interest_only', 'pending')                     | Ghi nhận trạng thái hoàn thành                                                  | 'success' (200 query), 'interest_only' (679 query).             |
| 10  | `stage_status`              |    `object` (dict)    |    **Có**    | Dict ghi nhận trạng thái từng giai đoạn (`interest`, `enrichment`, lý do bỏ qua)         | Ghi nhận theo tiến trình chạy pipeline                                          | Giúp resume và theo dõi circuit breaker.                        |
| 11  | `geo`                       |       `object`        |    **Có**    | Mã vùng địa lý thu thập                                                                  | Cấu hình crawl                                                                  | Cố định là 'VN' (Việt Nam).                                     |
| 12  | `date_range`                |       `object`        |    **Có**    | Phạm vi thời gian thu thập dữ liệu                                                       | Cấu hình crawl                                                                  | Cố định là 'all' (từ 2004 đến thời điểm crawl).                 |
| 13  | `interest_over_time`        |    `object` (dict)    |    **Có**    | Dict chứa mảng `timeline` (date, value) và thống kê (`average`, `max`, `nonzero_points`) | Dữ liệu chuỗi thời gian thô từ Google Trends                                    | Được phẳng hóa thành `trend_timeline.csv` & `trend_annual.csv`. |
| 14  | `interest_by_region`        |    `object` (dict)    |    **Có**    | Dict chứa mảng `regions` (region, rank, value) theo 63 tỉnh thành                        | Dữ liệu phân bổ địa lý thô                                                      | Được phẳng hóa thành `trend_regions.csv` (200 query).           |
| 15  | `commonly_searched_queries` |    `object` (dict)    |    **Có**    | Dict chứa danh sách truy vấn liên quan (`top_queries`, `rising_queries`)                 | Dữ liệu cụm từ liên quan thô                                                    | Được phẳng hóa thành `trend_related_queries.csv`.               |
| 16  | `errors`                    |    `object` (list)    |  **Không**   | Mảng ghi nhận thông báo lỗi nếu có trong quá trình gọi API                               | Ghi nhận lỗi HTTP/API                                                           | Không đưa vào dữ liệu cleaned phân tích.                        |

---

### File Raw: Bộ đệm Lưu trữ Phản hồi API (`trends-cache.sqlite3`)

- **Đường dẫn tệp:** `data-raw/google-trends/trends-cache.sqlite3`
- **Kích thước:** Bảng `trend_cache` gồm 1,079 dòng (dung lượng ~12.5 MB).
- **Mô tả:** Cơ sở dữ liệu SQLite3 trung gian dùng làm bộ đệm (cache) lưu phản hồi HTTP thô từ Google Trends, phục vụ cơ chế resume khi gặp lỗi quá tải HTTP 429 và kiểm thử offline.
- **Khóa chính:** `cache_key`.
- **Script xử lý tương ứng:** `scripts-fetching/unit-scripts/get_trends.py`.

| STT | Tên thuộc tính | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                        | Phương pháp làm sạch (nếu có)                 | Ghi chú (nếu có)                             |
| :-: | :------------- | :-------------------: | :----------: | :------------------------------------------------------- | :-------------------------------------------- | :------------------------------------------- |
|  1  | `cache_key`    |       `object`        |    **Có**    | Khóa định danh mục cache duy nhất                        | Chưa áp dụng (lưu trữ cache SQLite)           | Khóa chính cấp bảng SQLite (TEXT).           |
|  2  | `signature`    |       `object`        |    **Có**    | Chuỗi băm chữ ký tham số truy vấn                        | Băm SHA256/MD5 từ query + geo + date_range    | Dùng kiểm tra tính toàn vẹn của cache.       |
|  3  | `stage`        |       `object`        |    **Có**    | Giai đoạn thu thập ('interest' hoặc 'enrichment')        | Ghi nhận phân loại tầng crawl                 | Quản lý tiến độ 2 giai đoạn.                 |
|  4  | `query_id`     |       `object`        |    **Có**    | Mã băm định danh query tương ứng                         | Trùng khớp với `query_id` trong `trends.json` | Khóa ngoại mềm liên kết dữ liệu.             |
|  5  | `query_text`   |       `object`        |    **Có**    | Nội dung chuỗi truy vấn gửi lên Google Trends            | Chuỗi gốc (MID hoặc keyword)                  | TEXT.                                        |
|  6  | `query_kind`   |       `object`        |    **Có**    | Phân loại loại truy vấn ('topic_mid' hoặc 'search_term') | Ghi nhận loại truy vấn                        | TEXT.                                        |
|  7  | `geo`          |       `object`        |    **Có**    | Mã quốc gia/vùng địa lý truy vấn ('VN')                  | Cấu hình tham số                              | TEXT.                                        |
|  8  | `date_range`   |       `object`        |    **Có**    | Khung thời gian truy vấn ('all')                         | Cấu hình tham số                              | TEXT.                                        |
|  9  | `payload_json` |       `object`        |    **Có**    | Chuỗi JSON nguyên bản phản hồi từ Google Trends API      | Dữ liệu phản hồi thô nguyên vẹn               | Chứa toàn bộ response API để parse offline.  |
| 10  | `updated_at`   |       `object`        |    **Có**    | Dấu thời gian hệ thống ghi nhận/cập nhật bản ghi cache   | Định dạng chuẩn ISO 8601                      | Dùng theo dõi tuổi thọ và độ tươi của cache. |

---

### File Cleaned: Danh mục Truy vấn Đã Tối ưu (`trend_queries.csv`)

- **Đường dẫn tệp:** `data-cleaned/google-trends/trend_queries.csv`
- **Kích thước:** 879 dòng, 16 cột.
- **Mô tả:** Bảng định danh cấp cao cho 879 query Google Trends duy nhất sau khi tối ưu hóa và gom cụm từ 3,579 từ khóa ban đầu.
- **Khóa chính:** `query_id`.
- **Script xử lý tương ứng:** `scripts-processing/unit-scripts/clean_trends.py`.

| STT | Tên thuộc tính           | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                                  | Phương pháp làm sạch (nếu có)        | Ghi chú (nếu có)                                                  |
| :-: | :----------------------- | :-------------------: | :----------: | :----------------------------------------------------------------- | :----------------------------------- | :---------------------------------------------------------------- |
|  1  | `query_id`               |       `object`        |    **Có**    | Mã định danh duy nhất của query Google Trends                      | Trích xuất từ root của `trends.json` | Khóa chính, 879 giá trị duy nhất, 0 null.                         |
|  2  | `query`                  |       `object`        |    **Có**    | Chuỗi truy vấn gửi lên Google Trends (MID hoặc từ khóa)            | `clean_str()`, trích xuất nguyên bản | 0 null.                                                           |
|  3  | `query_kind`             |       `object`        |    **Có**    | Phân loại loại truy vấn ('topic_mid' hoặc 'search_term')           | Trích xuất nguyên bản                | Gồm 559 `topic_mid` và 320 `search_term`.                         |
|  4  | `mid`                    |       `object`        |    **Có**    | Mã Topic MID từ Google Trends                                      | Gán chuỗi rỗng `""` nếu null/None    | Có 320 dòng null/rỗng (36.4%) tương ứng với search_term fallback. |
|  5  | `title`                  |       `object`        |    **Có**    | Tiêu đề hiển thị của chủ đề từ Google Trends                       | Gán `""` nếu null/None               | 320 dòng null/rỗng (36.4%).                                       |
|  6  | `type`                   |       `object`        |    **Có**    | Phân loại ngữ nghĩa của topic từ Google Knowledge Graph            | Gán `""` nếu null/None               | 320 dòng null/rỗng (36.4%).                                       |
|  7  | `selection_score`        |       `float64`       |    **Có**    | Điểm số đánh giá độ tin cậy/liên quan của topic lựa chọn           | Trích xuất và ép kiểu                | Thang đo liên tục [0.0, 1.0].                                     |
|  8  | `status`                 |       `object`        |    **Có**    | Trạng thái thu thập tổng thể ('success' hoặc 'interest_only')      | Trích xuất nguyên bản                | Gồm 200 'success' (đủ 2 stage) và 679 'interest_only'.            |
|  9  | `stage_interest`         |       `object`        |    **Có**    | Trạng thái thu thập giai đoạn 1 (Interest over time)               | Trích xuất từ `stage_status`         | 100% đạt 'success'.                                               |
| 10  | `stage_enrichment`       |       `object`        |    **Có**    | Trạng thái thu thập giai đoạn 2 (Enrichment: region/related)       | Trích xuất từ `stage_status`         | Gồm 200 'success' và 679 'skipped'.                               |
| 11  | `enrichment_skip_reason` |       `object`        |    **Có**    | Lý do bỏ qua giai đoạn 2 ('low_interest', 'enrichment_limit')      | Gán chuỗi rỗng `""` nếu không skip   | Có 200 dòng rỗng (thành công), 679 dòng có lý do skip.            |
| 12  | `nonzero_points`         |        `int64`        |    **Có**    | Số tháng có mức độ quan tâm $> 0$ trong toàn lịch sử crawl         | Trích xuất từ `interest_over_time`   | Thước đo độ phủ dữ liệu (168 query có nonzero_points == 0).       |
| 13  | `average_interest`       |       `float64`       |    **Có**    | Mức độ quan tâm trung bình toàn lịch sử (thang 0–100)              | Trích xuất từ `interest_over_time`   | Đo lường mức độ phổ biến chung của query.                         |
| 14  | `max_interest`           |       `float64`       |    **Có**    | Mức độ quan tâm cao nhất ghi nhận được trong lịch sử (thang 0–100) | Trích xuất từ `interest_over_time`   | Đỉnh tìm kiếm lịch sử.                                            |
| 15  | `geo`                    |       `object`        |    **Có**    | Mã vùng địa lý thu thập dữ liệu ('VN')                             | Trích xuất nguyên bản                | Cố định là 'VN' (Việt Nam).                                       |
| 16  | `date_range`             |       `object`        |    **Có**    | Khung thời gian thu thập dữ liệu ('all')                           | Trích xuất nguyên bản                | Cố định là 'all' (từ 2004 đến thời điểm crawl).                   |

---

### File Cleaned: Ánh xạ Thực thể Tuyển sinh sang Query (`trend_keywords.csv`)

- **Đường dẫn tệp:** `data-cleaned/google-trends/trend_keywords.csv`
- **Kích thước:** 927 dòng, 8 cột.
- **Mô tả:** Bảng quan hệ ánh xạ nhiều-một ($N - 1$) giữa các từ khóa thực thể tuyển sinh tiếng Việt ban đầu và `query_id` của Google Trends.
- **Khóa liên kết:** `(query_id, keyword, keyword_type)`.
- **Script xử lý tương ứng:** `scripts-processing/unit-scripts/clean_trends.py`.

| STT | Tên thuộc tính     | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                              | Phương pháp làm sạch (nếu có)       | Ghi chú (nếu có)                                                                  |
| :-: | :----------------- | :-------------------: | :----------: | :------------------------------------------------------------- | :---------------------------------- | :-------------------------------------------------------------------------------- |
|  1  | `query_id`         |       `object`        |    **Có**    | Khóa ngoại tham chiếu đến bảng `trend_queries.csv`             | Trích xuất từ `keyword_metadata`    | Khóa ngoại liên kết, 0 null.                                                      |
|  2  | `keyword`          |       `object`        |    **Có**    | Tên từ khóa thực thể tuyển sinh gốc tiếng Việt                 | `clean_str()` xóa khoảng trắng thừa | 921 từ khóa duy nhất, 0 null.                                                     |
|  3  | `keyword_type`     |       `object`        |    **Có**    | Phân loại ngữ nghĩa từ khóa tuyển sinh (6 loại)                | `clean_str()`, chuẩn hóa chuỗi      | `school`, `major`, `major_group`, `subject`, `subject_group`, `admission_method`. |
|  4  | `selected_mid`     |       `object`        |    **Có**    | Mã Topic MID được thuật toán tuyển chọn gán cho từ khóa        | `clean_str()`                       | Có thể là MID Google hoặc keyword fallback.                                       |
|  5  | `selected_title`   |       `object`        |    **Có**    | Tiêu đề chủ đề được tuyển chọn gán cho từ khóa                 | `clean_str()`                       | Tiêu đề hiển thị chuẩn.                                                           |
|  6  | `relevance_score`  |       `float64`       |    **Có**    | Điểm số độ tương đồng ngữ nghĩa giữa từ khóa và topic          | Trích xuất từ metadata chấm điểm    | Thang đo liên tục [0.0, 1.0].                                                     |
|  7  | `selection_reason` |       `object`        |    **Có**    | Lý do lựa chọn ('best_relevant_topic' hoặc 'keyword_fallback') | Trích xuất từ metadata              | Thể hiện từ khóa có topic thật hay phải fallback.                                 |
|  8  | `candidate_count`  |        `int64`        |    **Có**    | Số lượng chủ đề ứng viên được tìm thấy ban đầu                 | Trích xuất từ metadata              | Thường từ 1 đến 5 ứng viên. Khử trùng lặp `drop_duplicates()`.                    |

---

### File Cleaned: Chuỗi Thời gian Mức độ Quan tâm theo Tháng (`trend_timeline.csv`)

- **Đường dẫn tệp:** `data-cleaned/google-trends/trend_timeline.csv`
- **Kích thước:** 240,846 dòng, 5 cột.
- **Mô tả:** Chuỗi thời gian mức độ quan tâm tìm kiếm theo từng tháng đồng bộ từ tháng 01/2004 đến tháng 10/2026 cho toàn bộ 879 query.
- **Khóa chính:** `(query_id, date)`.
- **Script xử lý tương ứng:** `scripts-processing/unit-scripts/clean_trends.py`.

| STT | Tên thuộc tính | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                                      | Phương pháp làm sạch (nếu có)                         | Ghi chú (nếu có)                                           |
| :-: | :------------- | :-------------------: | :----------: | :--------------------------------------------------------------------- | :---------------------------------------------------- | :--------------------------------------------------------- |
|  1  | `query_id`     |       `object`        |    **Có**    | Khóa ngoại tham chiếu đến bảng `trend_queries.csv`                     | Trích xuất từ `trends.json`                           | Khóa ngoại liên kết, 0 null.                               |
|  2  | `date`         |       `object`        |    **Có**    | Mốc thời gian quan sát theo tháng (chuẩn `YYYY-MM-DD`, ngày đầu tháng) | Cắt 10 ký tự đầu của chuỗi date thô (`raw_date[:10]`) | 274 mốc tháng liên tục (từ '2004-01-01' đến '2026-10-01'). |
|  3  | `year`         |        `int64`        |    **Có**    | Năm quan sát                                                           | Trích xuất từ 4 ký tự đầu của `date` và ép kiểu `int` | Phạm vi [2004, 2026], 0 null.                              |
|  4  | `month`        |        `int64`        |    **Có**    | Tháng quan sát trong năm (1 đến 12)                                    | Trích xuất từ ký tự 6:7 của `date` và ép kiểu `int`   | Phạm vi [1, 12], 0 null.                                   |
|  5  | `interest`     |        `int64`        |    **Có**    | Điểm mức độ quan tâm tìm kiếm chuẩn hóa của Google Trends              | Ép kiểu `int`                                         | Thang đo số nguyên tự nhiên [0, 100].                      |

---

### File Cleaned: Chỉ số Xu hướng Tổng hợp Năm & Mùa vụ (`trend_annual.csv`)

- **Đường dẫn tệp:** `data-cleaned/google-trends/trend_annual.csv`
- **Kích thước:** 20,217 dòng, 7 cột.
- **Mô tả:** Các chỉ số tổng hợp xu hướng tìm kiếm theo cấp năm (2004 đến 2026), bao gồm mức độ quan tâm trung bình, cực đại, tổng điểm và chỉ số mùa vụ cao điểm tuyển sinh.
- **Khóa chính:** `(query_id, year)`.
- **Script xử lý tương ứng:** `scripts-processing/unit-scripts/clean_trends.py`.

| STT | Tên thuộc tính         | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                                                | Phương pháp làm sạch (nếu có)                                                    | Ghi chú (nếu có)                                                                       |
| :-: | :--------------------- | :-------------------: | :----------: | :------------------------------------------------------------------------------- | :------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------- |
|  1  | `query_id`             |       `object`        |    **Có**    | Khóa ngoại tham chiếu đến bảng `trend_queries.csv`                               | Trích xuất từ `trends.json`                                                      | Khóa ngoại liên kết, 0 null.                                                           |
|  2  | `year`                 |        `int64`        |    **Có**    | Năm tổng hợp dữ liệu                                                             | Gom nhóm từ dữ liệu timeline                                                     | 23 năm (2004 đến 2026), 0 null.                                                        |
|  3  | `interest_mean`        |       `float64`       |    **Có**    | Điểm mức độ quan tâm trung bình cả năm                                           | Tính trung bình cộng của 12 tháng, làm tròn 4 chữ số thập phân (`round(..., 4)`) | Thang đo liên tục [0.0, 100.0].                                                        |
|  4  | `interest_max`         |        `int64`        |    **Có**    | Điểm mức độ quan tâm cao nhất trong năm                                          | Lấy giá trị lớn nhất trong 12 tháng (`max(vals)`)                                | Thang đo [0, 100].                                                                     |
|  5  | `interest_sum`         |        `int64`        |    **Có**    | Tổng điểm mức độ quan tâm của tất cả các tháng trong năm                         | Tính tổng cộng các tháng (`sum(vals)`)                                           | Giá trị nguyên $\ge 0$.                                                                |
|  6  | `interest_season_peak` |       `float64`       |    **Có**    | Điểm mức độ quan tâm trung bình trong mùa tuyển sinh cao điểm (tháng 5, 6, 7, 8) | Lọc các tháng 5, 6, 7, 8 và tính trung bình cộng, làm tròn 4 chữ số thập phân    | Lưu ý: đây là điểm cường độ mùa vụ, không phải là chỉ số tháng đỉnh (peak month 1–12). |
|  7  | `nonzero_months`       |        `int64`        |    **Có**    | Số tháng trong năm có điểm quan tâm $> 0$                                        | Đếm số tháng có `val > 0` trong năm                                              | Giá trị nguyên từ 0 đến 12.                                                            |

---

### File Cleaned: Mức độ Quan tâm theo Tỉnh/Thành phố (`trend_regions.csv`)

- **Đường dẫn tệp:** `data-cleaned/google-trends/trend_regions.csv`
- **Kích thước:** 10,195 dòng, 4 cột.
- **Mô tả:** Mức độ quan tâm tìm kiếm phân bổ theo 63 tỉnh/thành phố tại Việt Nam cho 196 query có tín hiệu cao nhất (giai đoạn enrichment).
- **Khóa liên kết:** `(query_id, region)`.
- **Script xử lý tương ứng:** `scripts-processing/unit-scripts/clean_trends.py`.

| STT | Tên thuộc tính | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                         | Phương pháp làm sạch (nếu có)      | Ghi chú (nếu có)                             |
| :-: | :------------- | :-------------------: | :----------: | :-------------------------------------------------------- | :--------------------------------- | :------------------------------------------- |
|  1  | `query_id`     |       `object`        |    **Có**    | Khóa ngoại tham chiếu đến bảng `trend_queries.csv`        | Trích xuất từ `interest_by_region` | Thuộc 196 query vượt qua enrichment, 0 null. |
|  2  | `region`       |       `object`        |    **Có**    | Tên tỉnh/thành phố tại Việt Nam                           | `clean_str()` chuẩn hóa chuỗi      | 63 tỉnh thành trực thuộc Trung ương, 0 null. |
|  3  | `rank`         |        `int64`        |    **Có**    | Thứ hạng mức độ quan tâm của tỉnh/thành phố đối với query | Trích xuất nguyên bản              | Hạng 1 là tỉnh quan tâm nhiều nhất.          |
|  4  | `value`        |        `int64`        |    **Có**    | Điểm mức độ quan tâm tương đối của tỉnh/thành phố         | Trích xuất nguyên bản              | Thang đo chuẩn hóa tương đối [0, 100].       |

---

### File Cleaned: Cụm từ Tìm kiếm Liên quan Top & Rising (`trend_related_queries.csv`)

- **Đường dẫn tệp:** `data-cleaned/google-trends/trend_related_queries.csv`
- **Kích thước:** 1,182 dòng, 7 cột.
- **Mô tả:** Danh sách các cụm từ tìm kiếm thực tế liên quan được tra cứu nhiều nhất (Top queries) hoặc có mức tăng trưởng đột biến (Rising queries) đi kèm với chủ đề tuyển sinh.
- **Khóa liên kết:** `(query_id, query_type, related_query)`.
- **Script xử lý tương ứng:** `scripts-processing/unit-scripts/clean_trends.py`.

| STT | Tên thuộc tính  | Kiểu dữ liệu (pandas) | Được sử dụng | Ý nghĩa (vắn tắt)                                                       | Phương pháp làm sạch (nếu có)                | Ghi chú (nếu có)                                                        |
| :-: | :-------------- | :-------------------: | :----------: | :---------------------------------------------------------------------- | :------------------------------------------- | :---------------------------------------------------------------------- |
|  1  | `query_id`      |       `object`        |    **Có**    | Khóa ngoại tham chiếu đến bảng `trend_queries.csv`                      | Trích xuất từ `commonly_searched_queries`    | Thuộc 89 query có phát sinh cụm từ liên quan, 0 null.                   |
|  2  | `query_type`    |       `object`        |    **Có**    | Phân loại nhóm truy vấn liên quan ('top' hoặc 'rising')                 | Phân tách từ cấu trúc dict                   | 'top' (tìm kiếm nhiều nhất) hoặc 'rising' (tăng trưởng nhanh).          |
|  3  | `related_query` |       `object`        |    **Có**    | Cụm từ tìm kiếm thực tế liên quan do người dùng gõ trên Google          | `clean_str()` xóa khoảng trắng thừa          | 647 cụm từ tìm kiếm duy nhất, 0 null.                                   |
|  4  | `rank`          |        `int64`        |    **Có**    | Thứ hạng của cụm từ trong nhóm kết quả liên quan                        | Trích xuất nguyên bản                        | Thứ hạng từ 1 đến 25.                                                   |
|  5  | `value`         |        `int64`        |    **Có**    | Giá trị đo lường mức độ quan tâm hoặc tỷ lệ phần trăm tăng trưởng       | Ép kiểu `int64`                              | Đối với 'top': điểm số [0, 100]; đối với 'rising': tỷ lệ % tăng trưởng. |
|  6  | `is_breakout`   |        `bool`         |    **Có**    | Cờ đánh dấu truy vấn có mức tăng trưởng bùng nổ (Breakout / $> 5000\%$) | Ép kiểu `bool(it.get('is_breakout', False))` | `True` nếu tăng trưởng đột biến, `False` nếu bình thường.               |
|  7  | `metric_type`   |       `object`        |    **Có**    | Loại đơn vị đo lường của trường `value` ('score' hoặc 'change')         | Gán tự động theo `query_type`                | 'score' cho nhóm top, 'change' cho nhóm rising.                         |

---

## Dữ liệu Phổ điểm Thi Tốt nghiệp THPT (Score Distributions)

### Tổng quan Nhánh Dữ liệu Phổ điểm (`data-raw/score-distribution/`)

- **Vị trí lưu trữ:** `data-raw/score-distribution/`
- **Trạng thái làm sạch:** **Không cần cleaned (sử dụng trực tiếp ở dạng thô)**. Dữ liệu được trích xuất nguyên bản từ hệ thống cơ sở dữ liệu công bố kết quả kỳ thi tốt nghiệp THPT quốc gia của Bộ Giáo dục & Đào tạo. Cấu trúc bảng đã chuẩn hóa theo từng thí sinh (hàng) và môn thi/tổ hợp (cột), có độ tin cậy tuyệt đối để ước lượng hàm phân phối tích lũy CDF ($F_{k, t}$) và phân vị ($R^*_{j, t}$) mà không cần lọc ngoại lai hay loại bỏ bản ghi.
- **Phân loại tệp dữ liệu:**
  1. `data-raw/score-distribution/score-distribution-2016-2025-ct2006.csv`:
     - **Dung lượng:** ~732.6 MB
     - **Số lượng bản ghi:** 8,535,859 dòng, 27 cột.
     - **Phạm vi nghiệp vụ:** Chứa điểm thi của các thí sinh dự thi theo **Chương trình giáo dục phổ thông 2006** từ năm 2016 đến 2025 (riêng dữ liệu năm 2025 chỉ bao gồm các thí sinh tự do dự thi theo chương trình 2006).
  2. `data-raw/score-distribution/score-distribution-2025-ct2018.csv`:
     - **Dung lượng:** ~73.0 MB
     - **Số lượng bản ghi:** 1,131,136 dòng, 26 cột.
     - **Phạm vi nghiệp vụ:** Chứa điểm thi của các thí sinh dự thi theo **Chương trình giáo dục phổ thông 2018 mới** bắt đầu áp dụng từ kỳ thi năm 2025 (và cấu trúc mở rộng áp dụng cho năm 2026 trở đi).

---

### Cấu trúc Thuộc tính Dữ liệu Phổ điểm theo Chương trình Giáo dục

#### 1. Format Chương trình 2006 (Giai đoạn 2016 – 2025)

> [!NOTE]
> Dữ liệu năm 2025 trong format này chỉ bao gồm thí sinh tự do dự thi theo Chương trình 2006.

| STT | Tên cột         | Kiểu dữ liệu (pandas) | Được sử dụng | Mô tả chi tiết & Quy tắc nghiệp vụ                                                                                                                              |
| :-: | :-------------- | :-------------------: | :----------: | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  1  | `SBD`           |  `object` / `int64`   |    **Có**    | Số báo danh gốc của thí sinh do Hội đồng thi cấp.                                                                                                               |
|  2  | `Nam`           |  `object` / `int64`   |    **Có**    | Năm thí sinh dự thi (dãy 2 số, từ `16` đến `25` tương ứng với 2016–2025; `20-2` và `21-2` tương ứng với đợt 2 của năm 2020 và 2021 do dịch Covid-19).           |
|  3  | `Tinh`          |        `int64`        |    **Có**    | Mã tỉnh hoặc thành phố dự thi của thí sinh (2 số, từ `01` đến `64` theo danh mục mã tỉnh BGD).                                                                  |
|  4  | `SBD_New`       |        `int64`        |    **Có**    | Số báo danh chuẩn hóa của thí sinh (6 số, từ 1 đến 108,573).                                                                                                    |
|  5  | `Toan`          |       `float64`       |    **Có**    | Điểm môn Toán (trắc nghiệm) theo thang điểm 10, gồm 50 câu (0.2 điểm/câu đúng).                                                                                 |
|  6  | `NguVan`        |       `float64`       |    **Có**    | Điểm môn Ngữ văn (tự luận) theo thang điểm 10, làm tròn đến 0.25 điểm.                                                                                          |
|  7  | `VatLy`         |       `float64`       |    **Có**    | Điểm môn Vật lí (trắc nghiệm) theo thang điểm 10, gồm 40 câu (0.25 điểm/câu đúng).                                                                              |
|  8  | `HoaHoc`        |       `float64`       |    **Có**    | Điểm môn Hóa học (trắc nghiệm) theo thang điểm 10, gồm 40 câu (0.25 điểm/câu đúng).                                                                             |
|  9  | `SinhHoc`       |       `float64`       |    **Có**    | Điểm môn Sinh học (trắc nghiệm) theo thang điểm 10, gồm 40 câu (0.25 điểm/câu đúng).                                                                            |
| 10  | `LichSu`        |       `float64`       |    **Có**    | Điểm môn Lịch sử (trắc nghiệm) theo thang điểm 10, gồm 40 câu (0.25 điểm/câu đúng).                                                                             |
| 11  | `DiaLy`         |       `float64`       |    **Có**    | Điểm môn Địa lí (trắc nghiệm) theo thang điểm 10, gồm 40 câu (0.25 điểm/câu đúng).                                                                              |
| 12  | `GDCD`          |       `float64`       |    **Có**    | Điểm môn Giáo dục công dân (trắc nghiệm) theo thang điểm 10, gồm 40 câu (0.25 điểm/câu đúng).                                                                   |
| 13  | `NgoaiNgu`      |       `float64`       |    **Có**    | Điểm của 1 trong 7 môn Ngoại ngữ (trắc nghiệm) theo thang điểm 10, gồm 40 câu (0.25 điểm/câu đúng).                                                             |
| 14  | `MaMonNgoaiNgu` |       `object`        |    **Có**    | Mã môn Ngoại ngữ dự thi: `N1` – Tiếng Anh; `N2` – Tiếng Nga; `N3` – Tiếng Pháp; `N4` – Tiếng Trung Quốc; `N5` – Tiếng Đức; `N6` – Tiếng Nhật; `N7` – Tiếng Hàn. |
| 15  | `TongDiem`      |       `float64`       |    **Có**    | Tổng điểm 6 môn thi theo thang điểm 60: $\text{Toán} + \text{Văn} + \text{Ngoại ngữ} + \max(\text{KHTN}, \text{KHXH})$.                                         |
| 16  | `KhoiA`         |       `float64`       |    **Có**    | Tổng điểm Tổ hợp A00 (Toán + Vật lí + Hóa học, thang 30). Loại trừ thí sinh không thi hoặc có môn = 0.                                                          |
| 17  | `KhoiA1`        |       `float64`       |    **Có**    | Tổng điểm Tổ hợp A01 (Toán + Vật lí + Ngoại ngữ, thang 30). Loại trừ thí sinh không thi hoặc có môn = 0.                                                        |
| 18  | `KhoiB`         |       `float64`       |    **Có**    | Tổng điểm Tổ hợp B00 (Toán + Hóa học + Sinh học, thang 30). Loại trừ thí sinh không thi hoặc có môn = 0.                                                        |
| 19  | `KhoiC`         |       `float64`       |    **Có**    | Tổng điểm Tổ hợp C00 (Ngữ văn + Lịch sử + Địa lí, thang 30). Loại trừ thí sinh không thi hoặc có môn = 0.                                                       |
| 20  | `KhoiD`         |       `float64`       |    **Có**    | Tổng điểm Tổ hợp D00 (Toán + Ngữ văn + Ngoại ngữ, thang 30). Loại trừ thí sinh không thi hoặc có môn = 0.                                                       |
| 21  | `KhoiA02`       |       `float64`       |    **Có**    | Tổng điểm Tổ hợp A02 (Toán + Vật lí + Sinh học, thang 30). Loại trừ thí sinh không thi hoặc có môn = 0.                                                         |
| 22  | `KhoiC01`       |       `float64`       |    **Có**    | Tổng điểm Tổ hợp C01 (Toán + Ngữ văn + Vật lí, thang 30). Loại trừ thí sinh không thi hoặc có môn = 0.                                                          |
| 23  | `KhoiD07`       |       `float64`       |    **Có**    | Tổng điểm Tổ hợp D07 (Toán + Hóa học + Ngoại ngữ, thang 30). Loại trừ thí sinh không thi hoặc có môn = 0.                                                       |
| 24  | `KHTN`          |       `float64`       |    **Có**    | Điểm trung bình cộng 3 môn bài thi Khoa học tự nhiên (Vật lí + Hóa học + Sinh học) / 3.                                                                         |
| 25  | `KHXH`          |       `float64`       |    **Có**    | Điểm trung bình cộng 3 môn bài thi Khoa học xã hội (Lịch sử + Địa lí + Giáo dục công dân) / 3.                                                                  |
| 26  | `TongDiemKHTN`  |       `float64`       |    **Có**    | Tổng điểm 6 môn thi bài thi KHTN (Toán + Ngữ văn + Ngoại ngữ + Vật lí + Hóa học + Sinh học, thang 60).                                                          |
| 27  | `TongDiemKHXH`  |       `float64`       |    **Có**    | Tổng điểm 6 môn thi bài thi KHXH (Toán + Ngữ văn + Ngoại ngữ + Lịch sử + Địa lí + GDCD, thang 60).                                                              |

---

#### 2. Format Chương trình 2018 (Từ Năm 2025 và 2026 trở đi)

> [!NOTE]
> Format mới phản ánh cấu trúc thi 4 môn: 2 môn bắt buộc (Toán, Ngữ văn) và 2 môn tự chọn trong số các môn Khoa học tự nhiên, Khoa học xã hội, Tin học và Công nghệ.

| STT | Tên cột              | Kiểu dữ liệu (pandas) | Được sử dụng | Mô tả chi tiết & Cấu trúc định dạng đề thi mới                                                                                                                  |
| :-: | :------------------- | :-------------------: | :----------: | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  1  | `SBD`                |  `object` / `int64`   |    **Có**    | Số báo danh gốc của thí sinh do Hội đồng thi cấp.                                                                                                               |
|  2  | `Nam`                |  `object` / `int64`   |    **Có**    | Năm dự thi (dãy 2 số: `25`, `26`...).                                                                                                                           |
|  3  | `Tinh`               |        `int64`        |    **Có**    | Mã tỉnh/thành phố dự thi (2 số: mã 01–64 đối với 2025; mã 01–96 từ 2026 trở đi).                                                                                |
|  4  | `SBD_New`            |        `int64`        |    **Có**    | Số báo danh chuẩn hóa của thí sinh (6 số, từ 1 đến 124,072 ở năm 2025; đến 139,678 ở năm 2026).                                                                 |
|  5  | `Toan`               |       `float64`       |    **Có**    | Điểm môn Toán (thang điểm 10): 12 câu trắc nghiệm nhiều lựa chọn (0.25đ/câu), 4 câu đúng/sai (0.1/0.25/0.5/1.0đ theo số ý đúng), 6 câu trả lời ngắn (0.5đ/câu). |
|  6  | `NguVan`             |       `float64`       |    **Có**    | Điểm môn Ngữ văn (tự luận) theo thang điểm 10, làm tròn tới 0.25 điểm.                                                                                          |
|  7  | `VatLy`              |       `float64`       |    **Có**    | Điểm môn Vật lí (thang 10): 18 câu trắc nghiệm (0.25đ), 4 câu đúng/sai, 6 câu trả lời ngắn (0.25đ).                                                             |
|  8  | `HoaHoc`             |       `float64`       |    **Có**    | Điểm môn Hóa học (thang 10): 18 câu trắc nghiệm (0.25đ), 4 câu đúng/sai, 6 câu trả lời ngắn (0.25đ).                                                            |
|  9  | `SinhHoc`            |       `float64`       |    **Có**    | Điểm môn Sinh học (thang 10): 18 câu trắc nghiệm (0.25đ), 4 câu đúng/sai, 6 câu trả lời ngắn (0.25đ).                                                           |
| 10  | `LichSu`             |       `float64`       |    **Có**    | Điểm môn Lịch sử (thang 10): 24 câu trắc nghiệm (0.25đ), 4 câu đúng/sai.                                                                                        |
| 11  | `DiaLy`              |       `float64`       |    **Có**    | Điểm môn Địa lí (thang 10): 18 câu trắc nghiệm (0.25đ), 4 câu đúng/sai, 6 câu trả lời ngắn (0.25đ).                                                             |
| 12  | `KinhTePhapLuat`     |       `float64`       |    **Có**    | Điểm môn Giáo dục Kinh tế và Pháp luật (thang 10): 24 câu trắc nghiệm (0.25đ), 4 câu đúng/sai.                                                                  |
| 13  | `TinHoc`             |       `float64`       |    **Có**    | Điểm môn Tin học (thang 10): 24 câu trắc nghiệm (0.25đ), 4 câu đúng/sai.                                                                                        |
| 14  | `CongNgheCongNghiep` |       `float64`       |    **Có**    | Điểm môn Công nghệ - Định hướng Công nghiệp (thang 10): 24 câu trắc nghiệm (0.25đ), 4 câu đúng/sai.                                                             |
| 15  | `CongNgheNongNghiep` |       `float64`       |    **Có**    | Điểm môn Công nghệ - Định hướng Nông nghiệp (thang 10): 24 câu trắc nghiệm (0.25đ), 4 câu đúng/sai.                                                             |
| 16  | `NgoaiNgu`           |       `float64`       |    **Có**    | Điểm 1 trong 7 môn Ngoại ngữ (trắc nghiệm) theo thang điểm 10 (40 câu, 0.25đ/câu).                                                                              |
| 17  | `MaMonNgoaiNgu`      |       `object`        |    **Có**    | Mã môn Ngoại ngữ: `N1` (Anh), `N2` (Nga), `N3` (Pháp), `N4` (Trung Quốc), `N5` (Đức), `N6` (Nhật), `N7` (Hàn).                                                  |
| 18  | `TongDiem`           |       `float64`       |    **Có**    | Tổng điểm 4 môn thi (Toán + Ngữ văn + 2 môn tự chọn) theo thang điểm 40.                                                                                        |
| 19  | `KhoiA`              |       `float64`       |    **Có**    | Tổng điểm Tổ hợp A00 (Toán + Vật lí + Hóa học, thang 30).                                                                                                       |
| 20  | `KhoiA1`             |       `float64`       |    **Có**    | Tổng điểm Tổ hợp A01 (Toán + Vật lí + Ngoại ngữ, thang 30).                                                                                                     |
| 21  | `KhoiB`              |       `float64`       |    **Có**    | Tổng điểm Tổ hợp B00 (Toán + Hóa học + Sinh học, thang 30).                                                                                                     |
| 22  | `KhoiC`              |       `float64`       |    **Có**    | Tổng điểm Tổ hợp C00 (Ngữ văn + Lịch sử + Địa lí, thang 30).                                                                                                    |
| 23  | `KhoiD`              |       `float64`       |    **Có**    | Tổng điểm Tổ hợp D00 (Toán + Ngữ văn + Ngoại ngữ, thang 30).                                                                                                    |
| 24  | `KhoiA02`            |       `float64`       |    **Có**    | Tổng điểm Tổ hợp A02 (Toán + Vật lí + Sinh học, thang 30).                                                                                                      |
| 25  | `KhoiC01`            |       `float64`       |    **Có**    | Tổng điểm Tổ hợp C01 (Toán + Ngữ văn + Vật lí, thang 30).                                                                                                       |
| 26  | `KhoiD07`            |       `float64`       |    **Có**    | Tổng điểm Tổ hợp D07 (Toán + Hóa học + Ngoại ngữ, thang 30).                                                                                                    |

---

### Danh mục Mã Tỉnh/Thành phố Dự thi (`Tinh`)

#### 1. Giai đoạn 2002 – 2025 (Mã 01 đến 64)

|   Mã   | Tỉnh / Thành phố |   Mã   | Tỉnh / Thành phố |   Mã   | Tỉnh / Thành phố    |   Mã   | Tỉnh / Thành phố       |
| :----: | :--------------- | :----: | :--------------- | :----: | :------------------ | :----: | :--------------------- |
| **01** | TP. Hà Nội       | **17** | Tỉnh Quảng Ninh  | **33** | Tỉnh Thừa Thiên Huế | **49** | Tỉnh Long An           |
| **02** | TP. Hồ Chí Minh  | **18** | Tỉnh Bắc Giang   | **34** | Tỉnh Quảng Nam      | **50** | Tỉnh Đồng Tháp         |
| **03** | TP. Hải Phòng    | **19** | Tỉnh Bắc Ninh    | **35** | Tỉnh Quảng Ngãi     | **51** | Tỉnh An Giang          |
| **04** | TP. Đà Nẵng      | **20** | Tỉnh Hà Tây (cũ) | **36** | Tỉnh Kon Tum        | **52** | Tỉnh Bà Rịa - Vũng Tàu |
| **05** | Tỉnh Hà Giang    | **21** | Tỉnh Hải Dương   | **37** | Tỉnh Bình Định      | **53** | Tỉnh Tiền Giang        |
| **06** | Tỉnh Cao Bằng    | **22** | Tỉnh Hưng Yên    | **38** | Tỉnh Gia Lai        | **54** | Tỉnh Kiên Giang        |
| **07** | Tỉnh Lai Châu    | **23** | Tỉnh Hòa Bình    | **39** | Tỉnh Phú Yên        | **55** | TP. Cần Thơ            |
| **08** | Tỉnh Lào Cai     | **24** | Tỉnh Hà Nam      | **40** | Tỉnh Đắk Lắk        | **56** | Tỉnh Bến Tre           |
| **09** | Tỉnh Tuyên Quang | **25** | Tỉnh Nam Định    | **41** | Tỉnh Khánh Hòa      | **57** | Tỉnh Vĩnh Long         |
| **10** | Tỉnh Lạng Sơn    | **26** | Tỉnh Thái Bình   | **42** | Tỉnh Lâm Đồng       | **58** | Tỉnh Trà Vinh          |
| **11** | Tỉnh Bắc Kạn     | **27** | Tỉnh Ninh Bình   | **43** | Tỉnh Bình Phước     | **59** | Tỉnh Sóc Trăng         |
| **12** | Tỉnh Thái Nguyên | **28** | Tỉnh Thanh Hóa   | **44** | Tỉnh Bình Dương     | **60** | Tỉnh Bạc Liêu          |
| **13** | Tỉnh Yên Bái     | **29** | Tỉnh Nghệ An     | **45** | Tỉnh Ninh Thuận     | **61** | Tỉnh Cà Mau            |
| **14** | Tỉnh Sơn La      | **30** | Tỉnh Hà Tĩnh     | **46** | Tỉnh Tây Ninh       | **62** | Tỉnh Điện Biên         |
| **15** | Tỉnh Phú Thọ     | **31** | Tỉnh Quảng Bình  | **47** | Tỉnh Bình Thuận     | **63** | Tỉnh Đắk Nông          |
| **16** | Tỉnh Vĩnh Phúc   | **32** | Tỉnh Quảng Trị   | **48** | Tỉnh Đồng Nai       | **64** | Tỉnh Hậu Giang         |

#### 2. Giai đoạn từ 2026 trở đi (Cập nhật mã định danh số)

| Mã số  | Tên tỉnh / Thành phố | Mã số  | Tên tỉnh / Thành phố | Mã số  | Tên tỉnh / Thành phố |
| :----: | :------------------- | :----: | :------------------- | :----: | :------------------- |
| **01** | TP. Hà Nội           | **24** | Tỉnh Bắc Ninh        | **56** | Tỉnh Khánh Hòa       |
| **04** | Tỉnh Cao Bằng        | **25** | Tỉnh Phú Thọ         | **66** | Tỉnh Đắk Lắk         |
| **08** | Tỉnh Tuyên Quang     | **31** | TP. Hải Phòng        | **68** | Tỉnh Lâm Đồng        |
| **11** | Tỉnh Điện Biên       | **33** | Tỉnh Hưng Yên        | **75** | Tỉnh Đồng Nai        |
| **12** | Tỉnh Lai Châu        | **37** | Tỉnh Ninh Bình       | **79** | TP. Hồ Chí Minh      |
| **14** | Tỉnh Sơn La          | **38** | Tỉnh Thanh Hóa       | **80** | Tỉnh Tây Ninh        |
| **15** | Tỉnh Lào Cai         | **40** | Tỉnh Nghệ An         | **82** | Tỉnh Đồng Tháp       |
| **19** | Tỉnh Thái Nguyên     | **42** | Tỉnh Hà Tĩnh         | **86** | Tỉnh Vĩnh Long       |
| **20** | Tỉnh Lạng Sơn        | **44** | Tỉnh Quảng Trị       | **91** | Tỉnh An Giang        |
| **22** | Tỉnh Quảng Ninh      | **46** | TP. Huế              | **92** | TP. Cần Thơ          |
| **48** | TP. Đà Nẵng          | **51** | Tỉnh Quảng Ngãi      | **52** | Tỉnh Gia Lai         |
| **96** | Tỉnh Cà Mau          |        |                      |        |                      |

---

### Bảng Ánh xạ các Cột Môn học sang Danh mục Môn trong `score-blocks.ipynb`

Dưới đây là 2 bảng đối soát ánh xạ 2 chiều giữa các cột trường dữ liệu trong dataset phổ điểm `score-distribution` và 67 thực thể môn học trích xuất từ notebook `scripts-processing/notebooks/score-blocks.ipynb`.

#### Bảng 1: Ánh xạ từ các Cột trong Dataset Phổ điểm (`score-distribution`) sang Môn học Tuyển sinh

| Cột trong `score-distribution`       | Áp dụng tại format | Môn học tương đương trong `score-blocks.ipynb` | Ghi chú chuyển đổi & Ý nghĩa nghiệp vụ                                                                              |
| :----------------------------------- | :----------------: | :--------------------------------------------- | :------------------------------------------------------------------------------------------------------------------ |
| `Toan`                               |    Cả 2 format     | `Toán`                                         | Khớp 1-1 chính xác.                                                                                                 |
| `NguVan`                             |    Cả 2 format     | `Ngữ văn`                                      | Khớp 1-1 chính xác.                                                                                                 |
| `VatLy`                              |    Cả 2 format     | `Vật lí`                                       | Đã chuẩn hóa chính tả 'Vật lý' $\rightarrow$ 'Vật lí'.                                                              |
| `HoaHoc`                             |    Cả 2 format     | `Hóa học`                                      | Khớp 1-1 chính xác.                                                                                                 |
| `SinhHoc`                            |    Cả 2 format     | `Sinh học`                                     | Khớp 1-1 chính xác.                                                                                                 |
| `LichSu`                             |    Cả 2 format     | `Lịch sử`                                      | Khớp 1-1 chính xác.                                                                                                 |
| `DiaLy`                              |    Cả 2 format     | `Địa lí`                                       | Đã chuẩn hóa chính tả 'Địa lý' $\rightarrow$ 'Địa lí'.                                                              |
| `GDCD`                               | CT2006 (2016–2025) | `Gdkt&pl`                                      | **Tương đương hoàn toàn** theo định hướng chương trình mới.                                                         |
| `KinhTePhapLuat`                     |  CT2018 (từ 2025)  | `Gdkt&pl`                                      | Khớp 1-1 với môn Giáo dục Kinh tế và Pháp luật.                                                                     |
| `TinHoc`                             |  CT2018 (từ 2025)  | `Tin học`                                      | Môn thi tốt nghiệp mới từ CT2018 (CT2006 không tổ chức thi).                                                        |
| `CongNgheCongNghiep`                 |  CT2018 (từ 2025)  | `Công nghệ công nghiệp`                        | Môn thi mới thuộc nhánh Công nghệ công nghiệp.                                                                      |
| `CongNgheNongNghiep`                 |  CT2018 (từ 2025)  | `Công nghệ nông nghiệp`                        | Môn thi mới thuộc nhánh Công nghệ nông nghiệp.                                                                      |
| `NgoaiNgu` (`MaMonNgoaiNgu == 'N1'`) |    Cả 2 format     | `Tiếng Anh`                                    | Môn Ngoại ngữ phổ biến nhất (>98% thí sinh).                                                                        |
| `NgoaiNgu` (`MaMonNgoaiNgu == 'N2'`) |    Cả 2 format     | `Tiếng Nga`                                    | Khớp qua mã `N2`.                                                                                                   |
| `NgoaiNgu` (`MaMonNgoaiNgu == 'N3'`) |    Cả 2 format     | `Tiếng Pháp`                                   | Khớp qua mã `N3`.                                                                                                   |
| `NgoaiNgu` (`MaMonNgoaiNgu == 'N4'`) |    Cả 2 format     | `Tiếng Trung`                                  | Khớp qua mã `N4`.                                                                                                   |
| `NgoaiNgu` (`MaMonNgoaiNgu == 'N5'`) |    Cả 2 format     | `Tiếng Đức`                                    | Khớp qua mã `N5`.                                                                                                   |
| `NgoaiNgu` (`MaMonNgoaiNgu == 'N6'`) |    Cả 2 format     | `Tiếng Nhật`                                   | Khớp qua mã `N6`.                                                                                                   |
| `NgoaiNgu` (`MaMonNgoaiNgu == 'N7'`) |    Cả 2 format     | `Tiếng Hàn`                                    | Khớp qua mã `N7`.                                                                                                   |
| `NgoaiNgu` (Cột tổng quát)           |    Cả 2 format     | `Ngoại ngữ`                                    | Áp dụng cho các tổ hợp chấp nhận điểm Ngoại ngữ bất kỳ.                                                             |
| `KHTN` / `TongDiemKHTN`              | CT2006 (2016–2025) | `Khoa học tự nhiên`                            | Điểm bài thi tổ hợp KHTN (CT2018 thi theo từng môn riêng lẻ).                                                       |
| `KHXH` / `TongDiemKHXH`              | CT2006 (2016–2025) | `Khoa học xã hội`                              | Điểm bài thi tổ hợp KHXH (CT2018 thi theo từng môn riêng lẻ).                                                       |
| Tổ hợp tự chọn 4 môn                 |  CT2018 (từ 2025)  | `Vật lí/Hóa học/Sinh học/Tin học`              | Thí sinh chọn 1 trong 4 môn: `VatLy`, `HoaHoc`, `SinhHoc`, `TinHoc` (đã chuẩn hóa `Sinh` $\rightarrow$ `Sinh học`). |

---

#### Bảng 2: Bảng Đối chiếu Toàn diện 65 Thực thể Môn học trong `score-blocks.ipynb` (Sau Chuẩn hóa Văn & Sinh) sang Cột Dataset Phổ điểm

> [!IMPORTANT]
>
> - Môn **GDCD** trong kỳ thi THPT truyền thống tương đương với môn **`Gdkt&pl`** (Giáo dục Kinh tế và Pháp luật) trong chương trình mới.
> - Đã bổ sung chuẩn hóa đồng nhất: **`Văn` $\rightarrow$ `Ngữ văn`** và **`Sinh` $\rightarrow$ `Sinh học`** (kể cả trong chuỗi gộp `Vật lí/Hóa học/Sinh học/Tin học`). Vì vậy tổng số thực thể duy nhất rút từ 67 xuống còn **65 thực thể** (1 `nan` và 64 môn học).
> - Các môn năng khiếu nghệ thuật, thể dục thể thao, sân khấu điện ảnh hoặc các bài thi đánh giá năng lực/đánh giá tư duy do các trường đại học tự tổ chức riêng không thuộc phạm vi kỳ thi THPT quốc gia của Bộ GD&ĐT, do đó được đánh dấu là **"Không tìm thấy"**.

| STT | Thực thể môn học trong `score-blocks.ipynb` | Cột tương ứng trong `score-distribution`    | Format dữ liệu áp dụng | Trạng thái ánh xạ & Ghi chú nghiệp vụ                                                             |
| :-: | :------------------------------------------ | :------------------------------------------ | :--------------------: | :------------------------------------------------------------------------------------------------ |
|  1  | `Toán`                                      | `Toan`                                      |      Cả 2 format       | **Khớp thành công**                                                                               |
|  2  | `Ngữ văn`                                   | `NguVan`                                    |      Cả 2 format       | **Khớp thành công** (Đã gộp từ `Văn` $\rightarrow$ `Ngữ văn`)                                     |
|  3  | `Tiếng Anh`                                 | `NgoaiNgu` (`MaMonNgoaiNgu == 'N1'`)        |      Cả 2 format       | **Khớp thành công** (Lọc theo mã `N1`)                                                            |
|  4  | `nan`                                       | _Không áp dụng_                             |           —            | Giá trị rỗng cho vị trí môn thứ 4 trong tổ hợp 3 môn.                                             |
|  5  | `Vật lí`                                    | `VatLy`                                     |      Cả 2 format       | **Khớp thành công**                                                                               |
|  6  | `Hóa học`                                   | `HoaHoc`                                    |      Cả 2 format       | **Khớp thành công**                                                                               |
|  7  | `Sinh học`                                  | `SinhHoc`                                   |      Cả 2 format       | **Khớp thành công** (Đã gộp từ `Sinh` $\rightarrow$ `Sinh học`)                                   |
|  8  | `Lịch sử`                                   | `LichSu`                                    |      Cả 2 format       | **Khớp thành công**                                                                               |
|  9  | `Địa lí`                                    | `DiaLy`                                     |      Cả 2 format       | **Khớp thành công**                                                                               |
| 10  | `Tiếng Pháp`                                | `NgoaiNgu` (`MaMonNgoaiNgu == 'N3'`)        |      Cả 2 format       | **Khớp thành công** (Lọc theo mã `N3`)                                                            |
| 11  | `Tiếng Trung`                               | `NgoaiNgu` (`MaMonNgoaiNgu == 'N4'`)        |      Cả 2 format       | **Khớp thành công** (Lọc theo mã `N4`)                                                            |
| 12  | `Tiếng Nhật`                                | `NgoaiNgu` (`MaMonNgoaiNgu == 'N6'`)        |      Cả 2 format       | **Khớp thành công** (Lọc theo mã `N6`)                                                            |
| 13  | `Gdkt&pl`                                   | `GDCD` (CT2006) / `KinhTePhapLuat` (CT2018) |      Cả 2 format       | **Khớp thành công** (_GDCD tương đương Gdkt&pl_)                                                  |
| 14  | `Tiếng Nga`                                 | `NgoaiNgu` (`MaMonNgoaiNgu == 'N2'`)        |      Cả 2 format       | **Khớp thành công** (Lọc theo mã `N2`)                                                            |
| 15  | `Tiếng Đức`                                 | `NgoaiNgu` (`MaMonNgoaiNgu == 'N5'`)        |      Cả 2 format       | **Khớp thành công** (Lọc theo mã `N5`)                                                            |
| 16  | `Vẽ hình họa mỹ thuật`                      | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 17  | `Tiếng Hàn`                                 | `NgoaiNgu` (`MaMonNgoaiNgu == 'N7'`)        |      Cả 2 format       | **Khớp thành công** (Lọc theo mã `N7`)                                                            |
| 18  | `Năng khiếu vẽ nghệ thuật 1`                | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 19  | `Năng khiếu vẽ nghệ thuật 2`                | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 20  | `Vẽ mỹ thuật`                               | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 21  | `Năng khiếu tdtt`                           | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 22  | `Năng khiếu thể dục thể thao`               | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 23  | `Năng khiếu`                                | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 24  | `Năng khiếu âm nhạc 1`                      | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 25  | `Năng khiếu âm nhạc 2`                      | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 26  | `Đọc diễn cảm`                              | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 27  | `Hát`                                       | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 28  | `Tin học`                                   | `TinHoc`                                    |    CT2018 (từ 2025)    | **Khớp thành công** (Môn mới từ 2025; CT2006: không tìm thấy).                                    |
| 29  | `Vẽ trang trí màu`                          | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 30  | `Vẽ năng khiếu`                             | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 31  | `Năng khiếu 1`                              | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 32  | `Năng khiếu 2`                              | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 33  | `Nk mầm non 1 (kể chuyện, đọc, diễn cảm)`   | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 34  | `Nk mầm non 2 (hát)`                        | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 35  | `Xướng âm`                                  | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 36  | `Biểu diễn nghệ thuật`                      | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 37  | `Năng khiếu skđa 1`                         | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 38  | `Năng khiếu skđa 2`                         | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 39  | `Hình họa`                                  | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 40  | `Trang trí`                                 | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 41  | `Nk1`                                       | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 42  | `Năng khiếu báo chí`                        | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 43  | `Xây dựng kịch bản sự kiện`                 | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 44  | `Đọc kể diễn cảm`                           | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 45  | `Hát - múa`                                 | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 46  | `Ký xướng âm`                               | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 47  | `Hát hoặc biểu diễn nhạc cụ`                | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 48  | `Công nghệ công nghiệp`                     | `CongNgheCongNghiep`                        |    CT2018 (từ 2025)    | **Khớp thành công** (Môn mới từ 2025; CT2006: không tìm thấy).                                    |
| 49  | `Công nghệ nông nghiệp`                     | `CongNgheNongNghiep`                        |    CT2018 (từ 2025)    | **Khớp thành công** (Môn mới từ 2025; CT2006: không tìm thấy).                                    |
| 50  | `Năng khiếu âm nhạc`                        | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 51  | `Năng khiếu thuyết trình`                   | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 52  | `Năng khiếu nghệ thuật`                     | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 53  | `Đọc hiểu`                                  | _Không tìm thấy_                            |           —            | Không tìm thấy (Bài thi Đánh giá tư duy/ĐGNL riêng của ĐHBK/ĐHQG).                                |
| 54  | `Tư duy khoa học giải quyết vấn đề`         | _Không tìm thấy_                            |           —            | Không tìm thấy (Bài thi Đánh giá tư duy riêng).                                                   |
| 55  | `Khoa học tự nhiên`                         | `KHTN` / `TongDiemKHTN`                     |   CT2006 (2016–2025)   | **Khớp thành công** (CT2018 thi theo môn tự chọn đơn lẻ).                                         |
| 56  | `Vật lí/Hóa học/Sinh học/Tin học`           | `VatLy`, `HoaHoc`, `SinhHoc`, `TinHoc`      |    CT2018 (từ 2025)    | **Khớp thành công** (Tổ hợp tự chọn 1 trong 4 môn; đã chuẩn hóa `Sinh` $\rightarrow$ `Sinh học`). |
| 57  | `Tư duy định lượng`                         | _Không tìm thấy_                            |           —            | Không tìm thấy (Bài thi Đánh giá năng lực riêng của ĐHQG).                                        |
| 58  | `Tư duy định tính`                          | _Không tìm thấy_                            |           —            | Không tìm thấy (Bài thi Đánh giá năng lực riêng của ĐHQG).                                        |
| 59  | `Khoa học/Tiếng Anh`                        | _Không tìm thấy_                            |           —            | Không tìm thấy (Bài thi Đánh giá năng lực riêng).                                                 |
| 60  | `Khoa học xã hội`                           | `KHXH` / `TongDiemKHXH`                     |   CT2006 (2016–2025)   | **Khớp thành công** (CT2018 thi theo môn tự chọn đơn lẻ).                                         |
| 61  | `Khoa học`                                  | _Không tìm thấy_                            |           —            | Không tìm thấy (Bài thi Đánh giá năng lực riêng).                                                 |
| 62  | `Năng khiếu văn hóa nghệ thuật`             | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 63  | `Năng khiếu đọc diễn cảm và hát`            | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |
| 64  | `Ngoại ngữ`                                 | `NgoaiNgu`                                  |      Cả 2 format       | **Khớp thành công** (Cột điểm chung của 7 môn ngoại ngữ).                                         |
| 65  | `Năng khiếu giáo dục mầm non`               | _Không tìm thấy_                            |           —            | Không tìm thấy (Môn năng khiếu trường tự tổ chức thi tuyển).                                      |

---

## Ma trận Quan hệ & Ràng buộc Khóa Nối Liên Bảng

### Bảng Ánh xạ Quan hệ Liên Tệp (Entity-Relationship Mappings)

| Bảng nguồn (Source Table)  | Thuộc tính khóa nối (Join Key)     | Bảng đích (Target Table)    | Thuộc tính khóa đích                                       | Loại quan hệ | Mục đích nghiệp vụ                                                                                    |
| :------------------------- | :--------------------------------- | :-------------------------- | :--------------------------------------------------------- | :----------: | :---------------------------------------------------------------------------------------------------- |
| `cutoff-scores.csv`        | `score_code`                       | `majors.csv`                | `score_codes` (chứa mã sau khi tách `;`)                   |   $N - 1$    | Ánh xạ mã ngành tuyển sinh sang Tên ngành chuẩn và Nhóm ngành (`major_group_name`).                   |
| `cutoff-scores.csv`        | `score_blocks` (tách `;`)          | `score-blocks.csv`          | `code`                                                     |   $N - M$    | Kiểm thực tính hợp lệ của tổ hợp xét tuyển và trích xuất môn thi thành phần.                          |
| `cutoff-scores.csv`        | `school_name` (chuẩn hóa)          | `trend_keywords.csv`        | `keyword` (với `keyword_type == 'school'`)                 |   $N - 1$    | Nối thực thể trường đại học sang `query_id` của Google Trends.                                        |
| `majors.csv`               | `major_name` / `major_group_name`  | `trend_keywords.csv`        | `keyword` (với `keyword_type in ['major', 'major_group']`) |   $N - 1$    | Nối thực thể ngành / nhóm ngành sang `query_id` của Google Trends.                                    |
| `trend_keywords.csv`       | `query_id`                         | `trend_queries.csv`         | `query_id`                                                 |   $N - 1$    | Lấy thông tin thuộc tính query, điểm liên quan và độ phủ tìm kiếm.                                    |
| `trend_queries.csv`        | `query_id`                         | `trend_timeline.csv`        | `query_id`                                                 |   $1 - N$    | Truy xuất chuỗi mức độ quan tâm theo tháng (`YYYY-MM-DD`).                                            |
| `trend_queries.csv`        | `query_id`                         | `trend_annual.csv`          | `query_id`                                                 |   $1 - N$    | Truy xuất chỉ số xu hướng tổng hợp năm, đỉnh mùa vụ và tăng trưởng YoY.                               |
| `trend_queries.csv`        | `query_id`                         | `trend_regions.csv`         | `query_id`                                                 |   $1 - N$    | Khảo sát mức độ quan tâm phân bổ theo từng tỉnh/thành phố.                                            |
| `trend_queries.csv`        | `query_id`                         | `trend_related_queries.csv` | `query_id`                                                 |   $1 - N$    | Khảo sát các chủ đề và cụm từ tìm kiếm mở rộng liên quan đến thương hiệu/ngành.                       |
| `score-distribution-*.csv` | `Nam` (2 số hoặc 4 số), môn/tổ hợp | `cutoff-scores.csv`         | `score_year`, `score_blocks`                               |   $N - M$    | Ánh xạ phân phối điểm thi THPT quốc gia để tính phân vị (Percentile rank $R^*_{j,t}$) cho điểm chuẩn. |

---

### Các Ràng buộc Nghiệp vụ & Cảnh báo Kỹ thuật Khi Khai Phá Dữ Liệu

1. **Ràng buộc Khóa Lịch sử Điểm chuẩn (Cutoff History Key):**
   - Đơn vị quan sát điểm chuẩn tuyển sinh không duy nhất ở cấp `(school_id, score_code, score_year)`. Có hơn 5,000 nhóm chứa nhiều mức điểm chuẩn khác nhau do khác biệt về tổ hợp môn (`score_blocks`), cơ sở đào tạo hoặc chương trình đào tạo đặc thù.
   - _Khuyến nghị:_ Khi tạo biến trễ (Lag features như `cutoff_lag1`, `cutoff_lag2`), bắt buộc phải đưa thêm `score_blocks` và `score_admission_name` vào tổ hợp khóa, hoặc áp dụng hàm tổng hợp có định nghĩa rõ ràng (VD: lấy trung bình hoặc điểm chuẩn theo tổ hợp chính), đồng thời kiểm tra tự liên kết theo đúng mốc thời gian $t - 1$, tránh trường hợp lấy nhầm dòng trong cùng năm.

2. **Quy tắc Tránh Rò rỉ Dữ liệu Tương lai (Data Leakage Prevention):**
   - Trong tệp `trend_annual.csv`, chỉ số `interest_mean` và `interest_season_peak` được tính từ toàn bộ 12 tháng hoặc các tháng 5–8 của năm $T$.
   - _Khuyến nghị:_ Nếu mốc thời gian dự đoán điểm chuẩn là trước đợt xét tuyển (ví dụ cuối tháng 3 hoặc cuối tháng 5), không được sử dụng dữ liệu Google Trends của các tháng sau mốc dự đoán để gán cho năm $T$. Cần cắt dữ liệu chuỗi thời gian từ bảng `trend_timeline.csv` tính đến đúng mốc cắt (Cutoff Date) dự báo.

3. **Hiện tượng Zero-interest & Cơ chế Fallback:**
   - Có $19.1\%$ query ($168/879$) hoàn toàn không có điểm tìm kiếm trong lịch sử (`nonzero_points == 0`) do lượng tra cứu quá thấp.
   - _Khuyến nghị:_ Bắt buộc thiết lập cơ chế điền khuyết phân cấp theo ngữ nghĩa: Khi ngành đào tạo thiếu dữ liệu Trends, fallback về xu hướng của Nhóm ngành (`major_group`), nếu tiếp tục thiếu thì fallback về trung vị toàn quốc, kèm theo cờ nhị phân đánh dấu trạng thái thiếu dữ liệu (`is_trend_missing`).

4. **Quy tắc Ánh xạ Phân vị Điểm chuẩn từ Phổ điểm (Score Distribution to Cutoff Percentile):**
   - Bộ dữ liệu `score-distribution` được giữ nguyên dạng thô (`raw data`) không qua tiền xử lý/làm sạch dạng bảng. Việc trích xuất phân phối tích lũy $F_{k, t}(x)$ được thực hiện on-the-fly hoặc thông qua bước offline aggregation theo từng tổ hợp $k$ và năm $t$.
   - Đối với các tổ hợp môn có môn năng khiếu hoặc bài thi riêng của trường đại học (_Không tìm thấy_ trong phổ điểm THPT quốc gia), không thể tính trực tiếp $F_{k, t}$ từ phổ điểm THPTQG mà cần fallback hoặc chuẩn hóa riêng (Z-score/Min-Max trên lịch sử điểm chuẩn).
