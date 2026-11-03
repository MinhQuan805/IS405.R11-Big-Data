"""Quality Gate & Validation Engine.
Enforces statistical thresholds and Bayes Error Floor guarantees.
"""

from typing import Dict, Any, Tuple
from admission_core.specs.contracts import (
    BAYES_ERROR_FLOOR_MSE, MAX_BAYES_GAP_MSE, MIN_R2_SCORE, MAX_RMSE_SCORE
)

class QualityGate:
    """Cổng kiểm định chất lượng tự động trước khi phát hành mô hình"""

    def __init__(self, criteria: Dict[str, Any] = None):
        c = criteria or {}
        self.max_rmse = c.get("max_rmse", MAX_RMSE_SCORE)
        self.min_r2 = c.get("min_r2", MIN_R2_SCORE)
        self.max_bayes_gap = c.get("max_bayes_gap_mse", MAX_BAYES_GAP_MSE)

    def validate(self, metrics: Dict[str, Any]) -> Tuple[bool, str]:
        rmse = metrics.get("5fold_cv_rmse", 1.0)
        r2 = metrics.get("5fold_cv_r2", 0.0)
        mse = metrics.get("5fold_cv_mse", 1.0)
        
        # 1. Kiểm tra RMSE
        if rmse > self.max_rmse:
            return False, f"Thất bại Quality Gate: RMSE={rmse:.4f} vượt trần cho phép ({self.max_rmse})"

        # 2. Kiểm tra R2
        if r2 < self.min_r2:
            return False, f"Thất bại Quality Gate: R2={r2:.4f} thấp hơn ngưỡng tối thiểu ({self.min_r2})"

        # 3. Kiểm tra Sàn sai số Bayes
        bayes_gap = mse - BAYES_ERROR_FLOOR_MSE
        if bayes_gap > self.max_bayes_gap:
            return False, f"Thất bại Quality Gate: Khoảng cách sàn Bayes ({bayes_gap:.5f}) vượt ngưỡng ({self.max_bayes_gap})"

        return True, "Chấp thuận Quality Gate: Mọi chỉ số đạt chuẩn chất lượng!"

