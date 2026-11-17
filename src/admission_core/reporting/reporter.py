"""Write measured out-of-time metrics without assuming gate success."""
from pathlib import Path


class ReportGenerator:
    @staticmethod
    def generate_markdown(metrics, output_path):
        lines = ["# Kết quả đánh giá mô hình", "",
                 f"Thời điểm huấn luyện {metrics.get('training_date', '')}.", "",
                 f"Số mẫu huấn luyện {metrics.get('training_samples', 0):,}.", "",
                 "Kiểm định theo cửa sổ năm mở rộng. Mỗi lần huấn luyện chỉ sử dụng năm trước năm kiểm tra.", "",
                 "| Chỉ số | Giá trị |", "| --- | --- |"]
        for name in ["rmse", "mae", "mse", "r2", "spearman_rho", "baseline_rmse", "coverage_80"]:
            value = metrics.get(name)
            formatted = f"{value:.6f}" if isinstance(value, (int, float)) else "Không xác định"
            lines.append(f"| {name} | {formatted} |")
        lines.extend(["", "| Năm kiểm tra | Số mẫu train | RMSE | R² | Bao phủ Q10–Q90 |",
                      "| --- | --- | --- | --- | --- |"])
        for fold in metrics.get("folds", []):
            lines.append(f"| {fold['test_year']} | {fold['train_samples']} | {fold['rmse']:.6f} | {fold['r2']:.6f} | {fold['coverage_80']:.4f} |")
        lines.extend(["", f"Kết quả kiểm định chất lượng {'đạt' if metrics.get('quality_gate_passed') else 'không đạt'}.",
                      "", metrics.get("quality_gate_message", "Chưa kiểm định"), ""])
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)
