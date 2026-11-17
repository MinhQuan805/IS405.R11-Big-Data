"""Empirical distribution contract and exact step-function lookup."""

import numpy as np
import pandas as pd
from admission_core.specs.contracts import BLOCK_NAME_MAP

YEAR_MAP = {str(year)[2:]: year for year in range(2016, 2100)}
YEAR_MAP.update({"20-2": 2020, "21-2": 2021})
CDF_KEYS = ["score_year", "block_name", "score_value"]
CDF_COLUMNS = CDF_KEYS + ["candidate_count", "total_candidates", "cdf_leq", "rank_pct_gt"]


def normalize_scores(frame, source):
    if set(CDF_KEYS).issubset(frame.columns):
        result = frame[CDF_KEYS].copy()
        result["block_name"] = result.block_name.replace(BLOCK_NAME_MAP)
    else:
        frame = frame.copy()
        if "score_year" not in frame:
            if "Nam" in frame:
                year_text = frame.Nam.astype(str)
                frame["score_year"] = year_text.map(YEAR_MAP).fillna(pd.to_numeric(year_text, errors="coerce"))
            elif source == "score_distribution_ct2018":
                frame["score_year"] = 2025
            else:
                raise ValueError("Phổ điểm thiếu score_year hoặc Nam")
        blocks = [name for name in BLOCK_NAME_MAP.values() if name in frame]
        if not blocks:
            raise ValueError("Phổ điểm không có tổ hợp được hỗ trợ")
        result = frame.melt(id_vars="score_year", value_vars=blocks,
                            var_name="block_name", value_name="score_value")[CDF_KEYS]
    result["score_year"] = pd.to_numeric(result.score_year, errors="coerce")
    result["score_value"] = pd.to_numeric(result.score_value, errors="coerce")
    valid = (result.score_year.between(2016, 2100) & result.score_year.mod(1).eq(0) &
             result.score_value.between(0, 30) & result.block_name.isin(BLOCK_NAME_MAP.values()))
    result = result.loc[valid].copy()
    result["score_year"] = result.score_year.astype("int32")
    return result


def summarize_scores(observations):
    counts = observations.groupby(CDF_KEYS, as_index=False).size().rename(
        columns={"size": "candidate_count"})
    return summarize_counts(counts)


def summarize_counts(counts):
    counts = counts.sort_values(CDF_KEYS).copy()
    groups = counts.groupby(CDF_KEYS[:2], sort=False)
    counts["total_candidates"] = groups.candidate_count.transform("sum")
    counts["cdf_leq"] = groups.candidate_count.cumsum() / counts.total_candidates
    counts["rank_pct_gt"] = 1.0 - counts.cdf_leq
    return counts[CDF_COLUMNS].reset_index(drop=True)


def validate_cdf(frame):
    if frame.empty or set(CDF_COLUMNS) - set(frame.columns):
        raise ValueError("CDF rỗng hoặc sai schema. Cần tạo lại CDF theo contract v3")
    if frame.duplicated(CDF_KEYS).any():
        raise ValueError("CDF trùng khóa")
    values = frame[CDF_COLUMNS].copy().sort_values(CDF_KEYS)
    if values.isna().any().any() or not np.isfinite(
            values.select_dtypes(include="number").to_numpy()).all():
        raise ValueError("CDF chứa dữ liệu thiếu hoặc không hữu hạn")
    expected = values.groupby(CDF_KEYS[:2]).candidate_count.transform("sum")
    cumulative = values.groupby(CDF_KEYS[:2]).candidate_count.cumsum() / expected
    if (values.candidate_count <= 0).any() or not np.allclose(expected, values.total_candidates):
        raise ValueError("CDF có tần suất hoặc mẫu số không hợp lệ")
    if not values.score_value.between(0, 30).all() or not np.allclose(
            cumulative, values.cdf_leq, atol=1e-10) or not np.allclose(
            values.rank_pct_gt, 1 - cumulative, atol=1e-10):
        raise ValueError("CDF không khớp tần suất tích lũy")
    return frame


class CDFLookup:
    def __init__(self, frame):
        validate_cdf(frame)
        self.groups = {}
        for key, group in frame.groupby(CDF_KEYS[:2]):
            group = group.sort_values("score_value")
            self.groups[(int(key[0]), key[1])] = (
                group.score_value.to_numpy(), group.cdf_leq.to_numpy())

    def rank(self, year, block, score):
        key = (int(year), BLOCK_NAME_MAP.get(block, block))
        if key not in self.groups:
            raise ValueError(f"Thiếu CDF cho năm {year}, tổ hợp {block}")
        scores, cumulative = self.groups[key]
        index = np.searchsorted(scores, score, side="right") - 1
        return 1.0 if index < 0 else float(1 - cumulative[index])
