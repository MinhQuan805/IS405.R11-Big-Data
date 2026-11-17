"""Validate finite evaluation metrics before promoting a candidate release."""

from typing import Dict, Any, Tuple
import math
from admission_core.specs.contracts import (
    BAYES_ERROR_FLOOR_MSE, MIN_R2_SCORE, MAX_RMSE_SCORE
)

class QualityGate:
    """Cổng kiểm định chất lượng tự động trước khi phát hành mô hình"""

    def __init__(self, criteria: Dict[str, Any] = None):
        c = criteria or {}
        self.max_rmse = c.get("max_rmse", MAX_RMSE_SCORE)
        self.min_r2 = c.get("min_r2", MIN_R2_SCORE)
        self.max_bayes_gap = c.get("max_bayes_gap_mse")

    def validate(self, metrics: Dict[str, Any]) -> Tuple[bool, str]:
        rmse = metrics.get("rmse", metrics.get("5fold_cv_rmse"))
        r2 = metrics.get("r2", metrics.get("5fold_cv_r2"))
        mse = metrics.get("mse", metrics.get("5fold_cv_mse"))
        if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in (rmse, r2, mse)):
            return False, "Metric bắt buộc bị thiếu hoặc không hữu hạn"
        if rmse < 0 or mse < 0 or r2 > 1:
            return False, "Metric ngoài miền hợp lệ"
        
        # 1. Kiểm tra RMSE
        if rmse > self.max_rmse:
            return False, f"Thất bại Quality Gate: RMSE={rmse:.4f} vượt trần cho phép ({self.max_rmse})"

        # 2. Kiểm tra R2
        if r2 < self.min_r2:
            return False, f"Thất bại Quality Gate: R2={r2:.4f} thấp hơn ngưỡng tối thiểu ({self.min_r2})"

        # Optional legacy comparison against a configured reference error.
        bayes_gap = mse - BAYES_ERROR_FLOOR_MSE
        if self.max_bayes_gap is not None and bayes_gap > self.max_bayes_gap:
            return False, f"Khoảng cách sai số tham chiếu ({bayes_gap:.5f}) vượt ngưỡng ({self.max_bayes_gap})"

        return True, "Chấp thuận Quality Gate: Mọi chỉ số đạt chuẩn chất lượng!"

