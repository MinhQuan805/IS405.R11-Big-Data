# Kết quả triển khai và kiểm chứng

## 1. Phạm vi thực nghiệm

Hồ sơ này lưu đợt kiểm chứng ban đầu trên dữ liệu tổng hợp có seed 42. Kết quả chạy trên dữ liệu thực được cập nhật trong `reports/real_data_results.md`.

Hai backend đã chạy tính CDF và tạo đặc trưng. Pipeline Spark đã hoàn thành huấn luyện, kiểm định chất lượng và phát hành một phiên bản model.

Bộ kiểm thử ghi nhận 31 trường hợp, 0 thất bại và 0 lỗi thực thi.

## 2. Kiểm định mô hình

Dữ liệu kiểm chứng mô hình có 22.000 dòng điểm, 8 tổ hợp, 480 dòng điểm chuẩn và 48 chương trình mỗi năm. Gold có 384 mẫu mang nhãn từ 2018–2025 và 48 dòng phục vụ năm 2026.

Cửa sổ mở rộng đánh giá 288 quan sát của các năm 2020–2025. Mỗi năm kiểm tra được dự báo bằng mô hình chỉ học từ những năm trước.

| Chỉ số | Giá trị |
| --- | --- |
| rmse | 0.020689 |
| mae | 0.016294 |
| r2 | 0.989349 |
| spearman_rho | 0.994158 |
| baseline_rmse | 0.020186 |
| coverage_80 | 0.736111 |

RMSE của mô hình cao hơn baseline dùng phân vị năm trước 0.000503. Độ bao phủ Q10–Q90 được đo trực tiếp và cần được so sánh với mức danh nghĩa 80% khi đánh giá bất định.

## 3. Hiệu năng hai backend

Spark chạy local[2] với 4 shuffle partition. Mỗi cấu hình được đo ba lần bằng tiến trình mới. Thời gian khởi tạo được lưu riêng trong số liệu thô.

| Dòng điểm | Quan sát tổ hợp | Backend | CDF trung vị [min–max] (s) | Features trung vị [min–max] (s) | Peak RSS trung vị (MiB) |
| --- | --- | --- | --- | --- | --- |
| 2,200 | 17,600 | local_pandas | 0.1224 [0.0515–0.1280] | 0.3200 [0.2969–0.3687] | 178.4 |
| 2,200 | 17,600 | apache_spark | 9.4784 [8.5466–10.0847] | 14.4835 [13.9761–16.0925] | 904.2 |
| 22,000 | 176,000 | local_pandas | 0.3614 [0.2645–0.3902] | 0.3764 [0.3571–0.3968] | 202.1 |
| 22,000 | 176,000 | apache_spark | 10.0727 [9.7521–10.6649] | 14.3572 [14.0533–14.5175] | 948.1 |
| 220,000 | 1,760,000 | local_pandas | 1.6021 [1.3897–1.6415] | 0.5241 [0.5153–0.5624] | 355.0 |
| 220,000 | 1,760,000 | apache_spark | 12.9146 [12.0473–13.2425] | 15.6814 [14.9702–16.1920] | 988.9 |

Toàn bộ CDF và Gold của hai backend khớp trong dung sai 1e-8 ở mọi lần lặp. Các mức dữ liệu này được dùng để quan sát chi phí thực thi cục bộ. Khả năng mở rộng nhiều nút cần được đo trên cụm máy tương ứng.

Peak RSS được lấy mẫu mỗi 50 ms và cộng theo cây tiến trình Python, JVM và worker. Cách đo này có thể đếm lặp trang bộ nhớ dùng chung.

## 4. Dịch vụ dự đoán

API đã xử lý 100 yêu cầu tuần tự sau 5 yêu cầu khởi động. p50 là 15.791 ms, p95 là 34.406 ms.

Yêu cầu được gửi qua HTTP đến hai chương trình trong bộ dữ liệu tổng hợp. CDF và model thực tham gia suy luận. Các kiểm thử bổ sung xác nhận input lỗi, trạng thái thiếu artifact và xác suất biến đổi theo điểm thi.

## 5. Môi trường và nguồn kiểm chứng

Hệ điều hành Windows-10-10.0.26200-SP0. Python 3.11.9. Máy có 16 CPU logic và 15.64 GiB RAM.

Spark sử dụng phiên bản 4.3.0. Windows local sử dụng Java 25 cùng filesystem Java NIO của GlobalMentor. Script cấu hình kiểm tra checksum JAR trước khi sử dụng.

Kết quả kiểm thử nằm trong `reports/tests-all.xml`. Số liệu HTTP nằm trong `reports/serving_verification.json`. Số đo hiệu năng và manifest dữ liệu được lưu trong `reports/benchmarks/`.

Hồ sơ nguồn mặc định được ghi trong `reports/input_inventory.json`. Hồ sơ dữ liệu tổng hợp dùng kiểm chứng được ghi trong `reports/verification_data_inventory.json`.

Chi tiết mô hình được lưu trong `reports/model_metadata_verified.json`. Các model nhị phân và dataset sinh ra được giữ trong `runs/verification/`.

## 6. Đối chiếu với dữ liệu tuyển sinh thực

Đợt chạy dữ liệu thực được ghi trong `reports/real_data_results.md`, gồm kiểm tra quần thể CT2006/CT2018, bản lặp năm 2020, phạm vi chương trình sau chuẩn bị dữ liệu, kiểm định theo năm và benchmark. Khi đánh giá khả năng dự báo của đề tài, sử dụng số liệu thực cùng phạm vi mẫu tương ứng.
