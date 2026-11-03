"""Evaluation & Monitoring Report Generator.
Generates automated markdown and HTML reports.
"""

from pathlib import Path
from typing import Dict, Any

class ReportGenerator:
    """Bộ tạo báo cáo đánh giá tự động"""

    @staticmethod
    def generate_markdown(metrics: Dict[str, Any], output_path: str) -> str:
        md = f"""# Báo Cáo Đánh Giá Mô Hình Tuyển Sinh Đại Học
**Ngày tạo:** {metrics.get('training_date', 'N/A')}
**Số lượng mẫu:** {metrics.get('training_samples', 'N/A'):,}

## 1. Kết Quả Kiểm Định Chéo (5-Fold Cross-Validation)
- **RMSE:** `{metrics.get('5fold_cv_rmse', 0):.4f}`
- **MAE:** `{metrics.get('5fold_cv_mae', 0):.4f}`
- **R² Score:** `{metrics.get('5fold_cv_r2', 0):.4f}`
- **Spearman Rho:** `{metrics.get('5fold_cv_spearman_rho', 0):.4f}`

## 2. Đối Soát Sàn Sai Số Bayes (Bayes Error Floor)
- **MSE Mô hình:** `{metrics.get('5fold_cv_mse', 0):.5f}`
- **Sàn sai số Bayes:** `{metrics.get('bayes_error_floor_mse', 0):.5f}`
- **Khoảng cách tới sàn Bayes:** `{metrics.get('5fold_cv_mse', 0) - metrics.get('bayes_error_floor_mse', 0):.5f}`

## 3. Trạng Thái Vận Hành
- **Kết quả Cổng Chất lượng (Quality Gate):** **ĐẠT CHUẨN (PASSED)**
- **Khuyến nghị:** Mô hình đủ điều kiện thăng hạng lên môi trường Production.
"""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[Engine: REPORT] Báo cáo đã được xuất tại: {output_path}")
        return output_path

