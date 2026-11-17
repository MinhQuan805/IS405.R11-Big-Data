# Kết quả đánh giá mô hình

Thời điểm huấn luyện 2026-11-12T19:41:01.305456+07:00.

Số mẫu huấn luyện 24,566.

Kiểm định theo cửa sổ năm mở rộng. Mỗi lần huấn luyện chỉ sử dụng năm trước năm kiểm tra.

| Chỉ số | Giá trị |
| --- | --- |
| rmse | 0.194184 |
| mae | 0.133830 |
| mse | 0.037707 |
| r2 | 0.699623 |
| spearman_rho | 0.818842 |
| baseline_rmse | 0.190712 |
| coverage_80 | 0.545138 |

| Năm kiểm tra | Số mẫu train | RMSE | R² | Bao phủ Q10–Q90 |
| --- | --- | --- | --- | --- |
| 2020 | 4738 | 0.180700 | 0.716182 | 0.2933 |
| 2021 | 7305 | 0.245429 | 0.521217 | 0.4075 |
| 2022 | 10247 | 0.192275 | 0.703479 | 0.6452 |
| 2023 | 13280 | 0.183335 | 0.736605 | 0.6804 |
| 2024 | 16568 | 0.175870 | 0.770096 | 0.5908 |
| 2025 | 20451 | 0.186992 | 0.687821 | 0.5757 |

Kết quả kiểm định chất lượng không đạt.

Thất bại Quality Gate: RMSE=0.1942 vượt trần cho phép (0.16)
