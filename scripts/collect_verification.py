"""Collect measured execution evidence into reproducible reports."""
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET
from admission_core.artifacts import resolve_release


def main():
    reports = Path("reports")
    destination = reports / "benchmarks"
    destination.mkdir(parents=True, exist_ok=True)
    release = resolve_release("runs/verification/apache_spark/models")
    metadata = json.loads((release / "model_metadata.json").read_text(encoding="utf-8"))
    metrics = metadata["performance_metrics"]
    suite = ET.parse(reports / "tests-all.xml").getroot().find("testsuite")
    if int(suite.attrib["failures"]) or int(suite.attrib["errors"]):
        raise RuntimeError("Kiểm thử còn lỗi")
    serving = json.loads((reports / "serving_verification.json").read_text(encoding="utf-8"))
    lines = ["# Kết quả triển khai và kiểm chứng", "",
             "## 1. Phạm vi thực nghiệm", "",
             "Hồ sơ này lưu đợt kiểm chứng ban đầu trên dữ liệu tổng hợp có seed 42. Kết quả chạy trên dữ liệu thực được cập nhật trong `reports/real_data_results.md`.", "",
             "Hai backend đã chạy tính CDF và tạo đặc trưng. Pipeline Spark đã hoàn thành huấn luyện, kiểm định chất lượng và phát hành một phiên bản model.", "",
             f"Bộ kiểm thử ghi nhận {suite.attrib['tests']} trường hợp, {suite.attrib['failures']} thất bại và {suite.attrib['errors']} lỗi thực thi.", "",
             "## 2. Kiểm định mô hình", "",
             "Dữ liệu kiểm chứng mô hình có 22.000 dòng điểm, 8 tổ hợp, 480 dòng điểm chuẩn và 48 chương trình mỗi năm. Gold có 384 mẫu mang nhãn từ 2018–2025 và 48 dòng phục vụ năm 2026.", "",
             "Cửa sổ mở rộng đánh giá 288 quan sát của các năm 2020–2025. Mỗi năm kiểm tra được dự báo bằng mô hình chỉ học từ những năm trước.", "",
             "| Chỉ số | Giá trị |", "| --- | --- |"]
    for key in ("rmse", "mae", "r2", "spearman_rho", "baseline_rmse", "coverage_80"):
        lines.append(f"| {key} | {metrics[key]:.6f} |")
    difference = metrics["rmse"] - metrics["baseline_rmse"]
    direction = "cao hơn" if difference > 0 else "thấp hơn"
    lines.extend(["", f"RMSE của mô hình {direction} baseline dùng phân vị năm trước {abs(difference):.6f}. Độ bao phủ Q10–Q90 được đo trực tiếp và cần được so sánh với mức danh nghĩa 80% khi đánh giá bất định.",
                  "", "## 3. Hiệu năng hai backend", "",
                  "Spark chạy local[2] với 4 shuffle partition. Mỗi cấu hình được đo ba lần bằng tiến trình mới. Thời gian khởi tạo được lưu riêng trong số liệu thô.", "",
                  "| Dòng điểm | Quan sát tổ hợp | Backend | CDF trung vị [min–max] (s) | Features trung vị [min–max] (s) | Peak RSS trung vị (MiB) |",
                  "| --- | --- | --- | --- | --- | --- |"])
    environment = None
    for rows in (2200, 22000, 220000):
        candidates = list(Path(f"runs/benchmark-{rows}").glob("*/results.json"))
        if not candidates:
            raise FileNotFoundError(f"Thiếu kết quả benchmark {rows}")
        source = max(candidates, key=lambda path: path.stat().st_mtime)
        result = json.loads(source.read_text(encoding="utf-8"))
        environment = result["environment"]
        if not result["output_parity"] or len(result["measurements"]) != 6:
            raise ValueError("Benchmark chưa đủ ba lần đo và kiểm tra tương đương")
        for backend in ("local_pandas", "apache_spark"):
            selected = [item for item in result["measurements"] if item["backend"] == backend]
            medians = [statistics.median(item[key] for item in selected)
                       for key in ("cdf_seconds", "features_seconds", "peak_tree_rss_mb")]
            cdf_values = [item["cdf_seconds"] for item in selected]
            feature_values = [item["features_seconds"] for item in selected]
            lines.append(f"| {rows:,} | {rows * 8:,} | {backend} | {medians[0]:.4f} [{min(cdf_values):.4f}–{max(cdf_values):.4f}] | {medians[1]:.4f} [{min(feature_values):.4f}–{max(feature_values):.4f}] | {medians[2]:.1f} |")
        shutil.copyfile(source, destination / f"scale-{rows}.json")
        shutil.copyfile(source.parent / "measurements.csv", destination / f"scale-{rows}.csv")
        shutil.copyfile(Path(f"runs/scale-{rows}/data_manifest.json"), destination / f"data-{rows}.json")
    lines.extend(["", "Toàn bộ CDF và Gold của hai backend khớp trong dung sai 1e-8 ở mọi lần lặp. Các mức dữ liệu này được dùng để quan sát chi phí thực thi cục bộ. Khả năng mở rộng nhiều nút cần được đo trên cụm máy tương ứng.",
                  "", "Peak RSS được lấy mẫu mỗi 50 ms và cộng theo cây tiến trình Python, JVM và worker. Cách đo này có thể đếm lặp trang bộ nhớ dùng chung.",
                  "", "## 4. Dịch vụ dự đoán", "",
                  f"API đã xử lý {serving['requests']} yêu cầu tuần tự sau {serving['warmup_requests']} yêu cầu khởi động. p50 là {serving['latency_p50_ms']:.3f} ms, p95 là {serving['latency_p95_ms']:.3f} ms.",
                  "", "Yêu cầu được gửi qua HTTP đến hai chương trình trong bộ dữ liệu tổng hợp. CDF và model thực tham gia suy luận. Các kiểm thử bổ sung xác nhận input lỗi, trạng thái thiếu artifact và xác suất biến đổi theo điểm thi.",
                  "", "## 5. Môi trường và nguồn kiểm chứng", "",
                  f"Hệ điều hành {environment['platform']}. Python {environment['python'].split()[0]}. Máy có {environment['cpu_count']} CPU logic và {environment['ram_gb']:.2f} GiB RAM.",
                  "", "Spark sử dụng phiên bản 4.3.0. Windows local sử dụng Java 25 cùng filesystem Java NIO của GlobalMentor. Script cấu hình kiểm tra checksum JAR trước khi sử dụng.",
                  "", "Kết quả kiểm thử nằm trong `reports/tests-all.xml`. Số liệu HTTP nằm trong `reports/serving_verification.json`. Số đo hiệu năng và manifest dữ liệu được lưu trong `reports/benchmarks/`.",
                  "", "Hồ sơ nguồn mặc định được ghi trong `reports/input_inventory.json`. Hồ sơ dữ liệu tổng hợp dùng kiểm chứng được ghi trong `reports/verification_data_inventory.json`.",
                  "", "Chi tiết mô hình được lưu trong `reports/model_metadata_verified.json`. Các model nhị phân và dataset sinh ra được giữ trong `runs/verification/`.",
                  "", "## 6. Đối chiếu với dữ liệu tuyển sinh thực", "",
                  "Đợt chạy dữ liệu thực được ghi trong `reports/real_data_results.md`, gồm kiểm tra quần thể CT2006/CT2018, bản lặp năm 2020, phạm vi chương trình sau chuẩn bị dữ liệu, kiểm định theo năm và benchmark. Khi đánh giá khả năng dự báo của đề tài, sử dụng số liệu thực cùng phạm vi mẫu tương ứng.", ""])
    (reports / "implementation_verification.md").write_text("\n".join(lines), encoding="utf-8")
    shutil.copyfile(release / "model_metadata.json", reports / "model_metadata_verified.json")
    (reports / "runtime_environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True)
    (reports / "dependency_versions.txt").write_text(freeze.stdout, encoding="utf-8")
    print(reports / "implementation_verification.md")


if __name__ == "__main__":
    main()
