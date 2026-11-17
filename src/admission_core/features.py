"""Feature definitions shared by batch training and serving."""
import pandas as pd
from admission_core.specs.contracts import BLOCK_NAME_MAP, OFFICIAL_FEATURES

KEYS = ["school_id", "score_code", "score_year"]
PROGRAM = ["school_id", "school_name", "score_code", "major_name", "major_group_name", "score_year"]
LOOKUP_COLUMNS = KEYS + ["school_name", "major_name", "allowed_blocks", "offering_carried_forward"] + OFFICIAL_FEATURES
INTERACTIONS = {
    "inter_prog_school": ("prog_pct_lag1", "school_pct_mean_lag1"),
    "inter_school_major": ("school_pct_mean_lag1", "major_pct_mean_lag1"),
    "inter_prog_blocks": ("prog_pct_lag1", "num_blocks"),
    "inter_school_blocks": ("school_pct_mean_lag1", "num_blocks"),
}


def parse_blocks(value):
    return sorted({part.strip() for part in str(value).split(";") if part.strip() in BLOCK_NAME_MAP})


def major_mapping(frame):
    mapping = frame.assign(score_code=frame.score_codes.str.split(";")).explode("score_code")
    mapping["score_code"] = mapping.score_code.str.strip()
    keys = major_join_keys(mapping.columns)
    mapping = mapping.loc[mapping.score_code.notna() & mapping.score_code.ne(""),
                          keys + ["major_name", "major_group_name"]].drop_duplicates()
    if mapping.duplicated(keys).any():
        raise ValueError("Mã chương trình có nhiều ánh xạ ngành. Cần chuẩn hóa danh mục")
    return mapping


def major_join_keys(columns):
    return [key for key in ("school_id", "score_code", "score_year") if key in columns]


def finish_features(frame):
    frame = frame.copy()
    hierarchy = ["school_pct_mean_lag1", "school_pct_min_lag1", "major_pct_mean_lag1", "group_pct_mean_lag1"]
    frame[hierarchy] = frame[hierarchy].fillna(0.5)
    frame["is_new_program"] = frame.prog_pct_lag1.isna().astype(int)
    frame["prog_pct_lag1"] = frame.prog_pct_lag1.fillna(
        0.5 * frame.school_pct_mean_lag1 + 0.5 * frame.major_pct_mean_lag1)
    frame["delta_prog_vs_school_mean"] = frame.prog_pct_lag1 - frame.school_pct_mean_lag1
    frame["delta_prog_vs_major_mean"] = frame.prog_pct_lag1 - frame.major_pct_mean_lag1
    frame[["trend_school_peak", "trend_group_mean"]] = frame[["trend_school_peak", "trend_group_mean"]].fillna(0)
    for name, (left, right) in INTERACTIONS.items():
        frame[name] = frame[left] * frame[right]
    return frame


def validate_gold(frame):
    import numpy as np
    if frame.empty or set(LOOKUP_COLUMNS + ["R_star"]) - set(frame.columns):
        raise ValueError("Gold rỗng hoặc thiếu cột")
    if frame.duplicated(KEYS).any() or frame[KEYS].isna().any().any():
        raise ValueError("Gold trùng hoặc thiếu khóa")
    if not np.isfinite(frame[OFFICIAL_FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("Đặc trưng có null, NaN hoặc vô cực")
    labels = frame.R_star.dropna()
    if not labels.between(0, 1).all():
        raise ValueError("Nhãn R_star ngoài miền [0,1]")
    return frame
