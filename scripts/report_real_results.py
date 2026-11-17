"""Summarize real-data preparation, measured parity, and temporal evaluation."""
import json
from pathlib import Path
import shutil
import statistics
import xml.etree.ElementTree as ET
import pandas as pd


def main():
    candidates = []
    for path in Path("models/versions").glob("*/model_metadata.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("training_data_kind") == "real":
            candidates.append(path)
    metadata_path = max(candidates, key=lambda path: path.stat().st_mtime)
    candidate = metadata_path.parent
    metrics = json.loads((candidate / "evaluation.json").read_text(encoding="utf-8"))
    preparation = json.loads(Path("data/data-cleaned/v3/prepared/preparation_report.json").read_text(encoding="utf-8"))
    audit = json.loads(Path("reports/real_data_audit.json").read_text(encoding="utf-8"))
    benchmark_path = max(Path("runs/real-data/benchmark-corrected").glob("*/results.json"), key=lambda path: path.stat().st_mtime)
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    cdf = pd.read_parquet("data/data-cleaned/v3/cdf_deduplicated.parquet")
    gold = pd.read_parquet("data/data-cleaned/v3/gold_deduplicated.parquet")
    output = Path("reports/real-data")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("model_metadata.json", "evaluation.json", "evaluation.md", "out_of_time_predictions.parquet"):
        shutil.copyfile(candidate / name, output / name)
    shutil.copyfile(benchmark_path, output / "benchmark.json")
    shutil.copyfile(benchmark_path.parent / "measurements.csv", output / "benchmark.csv")
    shutil.copyfile("data/data-cleaned/v3/prepared/preparation_report.json", output / "preparation.json")
    suite = ET.parse("reports/tests-all.xml").getroot().find("testsuite")
    lines = ["# Kết quả xử lý dữ liệu tuyển sinh thực", "",
        "## 1. Nguồn và phạm vi", "",
        f"Bộ kiểm thử hiện tại có {suite.attrib['tests']} trường hợp, {suite.attrib['failures']} thất bại và {suite.attrib['errors']} lỗi thực thi.", "",
        "Nguồn CT2006 có 8.535.859 dòng, nguồn CT2018 có 1.131.136 dòng. Tổng đầu vào là 9.666.995 dòng. Bảng điểm chuẩn đã làm sạch có 101.466 dòng.", "",
        "Hai nguồn không trùng số báo danh trong năm 2025. Nguồn CT2006 có 10.857 bản ghi đợt 20-2 trùng hoàn toàn các giá trị của đợt 20, ngoại trừ nhãn đợt và mã được tạo lại. Cấu hình loại nhãn 20-2 trước khi tính phân phối.", "",
        f"Sau loại bản lặp còn 9.656.138 lượt quan sát đầu vào. CDF có {len(cdf):,} mốc và {int(cdf.candidate_count.sum()):,} quan sát điểm tổ hợp hợp lệ. Mỗi thí sinh có thể đóng góp vào nhiều tổ hợp.", "",
        "## 2. Chuẩn bị điểm chuẩn và danh mục ngành", "",
        "| Nguyên nhân loại | Số dòng |", "| --- | --- |"]
    for reason, count in preparation["exclusions"].items():
        lines.append(f"| {reason} | {count:,} |")
    lines.extend(["", f"Giữ lại {preparation['retained_rows']:,} dòng điểm chuẩn, tương ứng {preparation['retained_program_years']:,} khóa chương trình–năm trước khi lọc thời kỳ huấn luyện.",
        "", f"Danh mục nguồn có {audit['ambiguous_major_code_count']:,} mã xuất hiện ở nhiều ngành. Hệ thống phân giải bằng mã cùng tên chương trình theo trường và năm. Các trường hợp chưa phân giải được hoặc có xung đột được lưu trong `data/data-cleaned/v3/prepared/excluded-cutoffs.parquet`.",
        "", "Các kết quả phân giải có thể rà soát trong `mapping_review.csv`. Quy tắc chuỗi ký tự chưa thay thế việc kiểm tra thủ công các chuyên ngành và chương trình liên ngành.",
        "", f"Gold có {len(gold):,} dòng, gồm {int(gold.R_star.notna().sum()):,} mẫu mang nhãn và {int(gold.R_star.isna().sum()):,} dòng năm dự báo.",
        "", "## 3. Kiểm định theo năm", "",
        "| Chỉ số | Giá trị |", "| --- | --- |"])
    for name in ("rmse", "mae", "r2", "spearman_rho", "baseline_rmse", "coverage_80"):
        lines.append(f"| {name} | {metrics[name]:.6f} |")
    lines.extend(["", "| Năm kiểm tra | RMSE | R² | Bao phủ Q10–Q90 |", "| --- | --- | --- | --- |"])
    for fold in metrics["folds"]:
        lines.append(f"| {fold['test_year']} | {fold['rmse']:.6f} | {fold['r2']:.6f} | {fold['coverage_80']:.4f} |")
    lines.extend(["", "| Nhóm chương trình | Số mẫu | RMSE |", "| --- | --- | --- |"])
    for name, values in metrics["subgroups"].items():
        lines.append(f"| {name} | {values['samples']:,} | {values['rmse']:.6f} |")
    passed = metrics["quality_gate_passed"]
    lines.extend(["", f"Cổng chất lượng {'đạt' if passed else 'không đạt'}. {metrics['quality_gate_message']}",
        "", f"Mô hình ứng viên được lưu tại `{candidate.as_posix()}`. Trạng thái phát hành được quyết định bởi kết quả kiểm định chất lượng.",
        "", "## 4. Đối chiếu backend trên toàn bộ dữ liệu", "",
        "| Backend | Số lần | CDF trung vị (s) | Features trung vị (s) | Toàn luồng trung vị (s) | Peak RSS trung vị (MiB) |",
        "| --- | --- | --- | --- | --- | --- |"])
    for backend in ("local_pandas", "apache_spark"):
        rows = [row for row in benchmark["measurements"] if row["backend"] == backend]
        numbers = [statistics.median(row[key] for row in rows) for key in
                   ("cdf_seconds", "features_seconds", "processing_total_seconds", "peak_tree_rss_mb")]
        lines.append(f"| {backend} | {len(rows)} | {numbers[0]:.3f} | {numbers[1]:.3f} | {numbers[2]:.3f} | {numbers[3]:.1f} |")
    lines.extend(["", f"Kiểm tra tương đương toàn bộ CDF và Gold {'đạt' if benchmark['output_parity'] else 'không đạt'}. Dung sai số thực là 1e-8. Spark dùng local[2] và 4 shuffle partition.",
        "", "Pandas đọc Parquet theo lô 25.000 dòng và tổng hợp tần suất từng lô. Lượt benchmark đầu gặp thiếu bộ nhớ, được lưu ở `runs/real-data/benchmark.log`. Các số liệu trong bảng lấy từ lượt chạy đã giảm kích thước lô và giới hạn đọc trước của Arrow.",
        "", "Thời gian toàn luồng gồm khởi tạo, CDF và tạo đặc trưng, chưa gồm huấn luyện LightGBM. RAM là tổng RSS của cây tiến trình, lấy mẫu mỗi 50 ms. Thời gian khởi tạo và từng lần đo được lưu trong `reports/real-data/benchmark.json` cùng `benchmark.csv`.",
        "", "## 5. Giới hạn phục vụ", "",
        "Nguồn điểm thi hiện có đến năm 2025, còn mô hình cuối cùng xây dựng đặc trưng cho năm 2026. Khi chưa có CDF năm 2026, API từ chối yêu cầu cần phân vị năm đó. Kết quả đánh giá và trạng thái cổng chất lượng cần được xem trước khi sử dụng một phiên bản để phục vụ.",
        "", "Hướng dẫn thuật toán và các lệnh thực thi được trình bày trong `docs/huong-dan-he-thong.md`.", ""])
    Path("reports/real_data_results.md").write_text("\n".join(lines), encoding="utf-8")
    print("reports/real_data_results.md")


if __name__ == "__main__":
    main()
