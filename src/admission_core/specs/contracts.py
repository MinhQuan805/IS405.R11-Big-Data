"""Data Contract Specifications and Constants.
Defines invariant features, target constraints, and data validation rules.
"""

from typing import List, Dict, Any

# 16 đặc trưng chính thức vượt qua kiểm định ANOVA F-test
OFFICIAL_FEATURES: List[str] = [
    "prog_pct_lag1",
    "school_pct_mean_lag1",
    "school_pct_min_lag1",
    "major_pct_mean_lag1",
    "group_pct_mean_lag1",
    "delta_prog_vs_school_mean",
    "delta_prog_vs_major_mean",
    "num_blocks",
    "trend_school_peak",
    "trend_group_mean",
    "is_cutoff_over_30",
    "is_new_program",
    "inter_prog_school",
    "inter_school_major",
    "inter_prog_blocks",
    "inter_school_blocks",
]

TARGET_FEATURE: str = "R_star"

# Ngưỡng sàn sai số Bayes & Tiêu chí Quality Gate
BAYES_ERROR_FLOOR_MSE: float = 0.02283
MAX_BAYES_GAP_MSE: float = 0.005
MIN_R2_SCORE: float = 0.78
MAX_RMSE_SCORE: float = 0.160

# Danh mục các khối thi chuẩn hóa cho kỳ thi THPT
BLOCK_NAME_MAP: Dict[str, str] = {
    "A00": "KhoiA",
    "A01": "KhoiA1",
    "B00": "KhoiB",
    "C00": "KhoiC",
    "D01": "KhoiD",
    "A02": "KhoiA02",
    "C01": "KhoiC01",
    "D07": "KhoiD07",
}

def validate_feature_matrix(df) -> bool:
    """Kiểm tra tính hợp lệ của ma trận đặc trưng theo Hợp đồng dữ liệu"""
    missing_cols = [c for c in OFFICIAL_FEATURES if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Dữ liệu thiếu các đặc trưng bắt buộc theo Data Contract: {missing_cols}")
    return True

