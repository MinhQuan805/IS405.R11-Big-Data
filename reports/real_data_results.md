# Kết quả xử lý dữ liệu tuyển sinh thực

## 1. Nguồn và phạm vi

Bộ kiểm thử hiện tại có 36 trường hợp, 0 thất bại và 0 lỗi thực thi.

Nguồn CT2006 có 8.535.859 dòng, nguồn CT2018 có 1.131.136 dòng. Tổng đầu vào là 9.666.995 dòng. Bảng điểm chuẩn đã làm sạch có 101.466 dòng.

Hai nguồn không trùng số báo danh trong năm 2025. Nguồn CT2006 có 10.857 bản ghi đợt 20-2 trùng hoàn toàn các giá trị của đợt 20, ngoại trừ nhãn đợt và mã được tạo lại. Cấu hình loại nhãn 20-2 trước khi tính phân phối.

Sau loại bản lặp còn 9.656.138 lượt quan sát đầu vào. CDF có 54,647 mốc và 31,092,351 quan sát điểm tổ hợp hợp lệ. Mỗi thí sinh có thể đóng góp vào nhiều tổ hợp.

## 2. Chuẩn bị điểm chuẩn và danh mục ngành

| Nguyên nhân loại | Số dòng |
| --- | --- |
| other_admission_method | 44,066 |
| before_2016 | 12,734 |
| non_university | 2 |
| cutoff_outside_30_scale | 401 |
| no_supported_block | 4,649 |
| unresolved_or_conflicting_major | 8,285 |

Giữ lại 31,329 dòng điểm chuẩn, tương ứng 28,133 khóa chương trình–năm trước khi lọc thời kỳ huấn luyện.

Danh mục nguồn có 1,014 mã xuất hiện ở nhiều ngành. Hệ thống phân giải bằng mã cùng tên chương trình theo trường và năm. Các trường hợp chưa phân giải được hoặc có xung đột được lưu trong `data/data-cleaned/v3/prepared/excluded-cutoffs.parquet`.

Các kết quả phân giải có thể rà soát trong `mapping_review.csv`. Quy tắc chuỗi ký tự chưa thay thế việc kiểm tra thủ công các chuyên ngành và chương trình liên ngành.

Gold có 28,681 dòng, gồm 24,566 mẫu mang nhãn và 4,115 dòng năm dự báo.

## 3. Kiểm định theo năm

| Chỉ số | Giá trị |
| --- | --- |
| rmse | 0.194184 |
| mae | 0.133830 |
| r2 | 0.699623 |
| spearman_rho | 0.818842 |
| baseline_rmse | 0.190712 |
| coverage_80 | 0.545138 |

| Năm kiểm tra | RMSE | R² | Bao phủ Q10–Q90 |
| --- | --- | --- | --- |
| 2020 | 0.180700 | 0.716182 | 0.2933 |
| 2021 | 0.245429 | 0.521217 | 0.4075 |
| 2022 | 0.192275 | 0.703479 | 0.6452 |
| 2023 | 0.183335 | 0.736605 | 0.6804 |
| 2024 | 0.175870 | 0.770096 | 0.5908 |
| 2025 | 0.186992 | 0.687821 | 0.5757 |

| Nhóm chương trình | Số mẫu | RMSE |
| --- | --- | --- |
| existing | 16,272 | 0.179628 |
| new | 3,556 | 0.250212 |

Cổng chất lượng không đạt. Thất bại Quality Gate: RMSE=0.1942 vượt trần cho phép (0.16)

Mô hình ứng viên được lưu tại `models/versions/c47f7adefffc4df8a708d3aabeca8099`. Trạng thái phát hành được quyết định bởi kết quả kiểm định chất lượng.

## 4. Đối chiếu backend trên toàn bộ dữ liệu

| Backend | Số lần | CDF trung vị (s) | Features trung vị (s) | Toàn luồng trung vị (s) | Peak RSS trung vị (MiB) |
| --- | --- | --- | --- | --- | --- |
| local_pandas | 3 | 44.821 | 4.225 | 49.046 | 446.6 |
| apache_spark | 3 | 24.844 | 17.867 | 63.809 | 1122.4 |

Kiểm tra tương đương toàn bộ CDF và Gold đạt. Dung sai số thực là 1e-8. Spark dùng local[2] và 4 shuffle partition.

Pandas đọc Parquet theo lô 25.000 dòng và tổng hợp tần suất từng lô. Lượt benchmark đầu gặp thiếu bộ nhớ, được lưu ở `runs/real-data/benchmark.log`. Các số liệu trong bảng lấy từ lượt chạy đã giảm kích thước lô và giới hạn đọc trước của Arrow.

Thời gian toàn luồng gồm khởi tạo, CDF và tạo đặc trưng, chưa gồm huấn luyện LightGBM. RAM là tổng RSS của cây tiến trình, lấy mẫu mỗi 50 ms. Thời gian khởi tạo và từng lần đo được lưu trong `reports/real-data/benchmark.json` cùng `benchmark.csv`.

## 5. Giới hạn phục vụ

Nguồn điểm thi hiện có đến năm 2025, còn mô hình cuối cùng xây dựng đặc trưng cho năm 2026. Khi chưa có CDF năm 2026, API từ chối yêu cầu cần phân vị năm đó. Kết quả đánh giá và trạng thái cổng chất lượng cần được xem trước khi sử dụng một phiên bản để phục vụ.

Hướng dẫn thuật toán và các lệnh thực thi được trình bày trong `docs/huong-dan-he-thong.md`.
