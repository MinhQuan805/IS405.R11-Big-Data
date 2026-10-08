import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional

class AnchorNormalizer:
    """
    Thuật toán chuẩn hóa thang đo giữa các batch dữ liệu Google Trends 
    bằng từ khóa mốc (Anchor Keyword Normalization).
    
    Giải quyết triệt để hạn chế 5 từ khóa/request của Google Trends,
    giúp đưa tất cả từ khóa về cùng một hệ quy chiếu [0, 100] phục vụ huấn luyện Machine Learning.
    """
    def __init__(self, anchor_keyword: str, logger: Optional[logging.Logger] = None):
        self.anchor_keyword = anchor_keyword
        self.logger = logger or logging.getLogger("AnchorNormalizer")

    def normalize_time_series_batches(
        self,
        batch_dfs: List[pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Chuẩn hóa danh sách các Dataframe theo tuần (time series) về cùng một hệ quy chiếu.
        Mỗi DataFrame trong batch_dfs phải chứa cột anchor_keyword.
        """
        if not batch_dfs:
            return pd.DataFrame()
        if len(batch_dfs) == 1:
            df = batch_dfs[0].copy()
            if "isPartial" in df.columns:
                df = df.drop(columns=["isPartial"])
            return df

        # Lấy DataFrame đầu tiên làm mốc tham chiếu cơ sở (Base Reference)
        base_df = batch_dfs[0].copy()
        if "isPartial" in base_df.columns:
            base_df = base_df.drop(columns=["isPartial"])

        if self.anchor_keyword not in base_df.columns:
            raise ValueError(f"Batch cơ sở không chứa từ khóa mốc: '{self.anchor_keyword}'")

        master_df = base_df.copy()
        ref_anchor_series = base_df[self.anchor_keyword].astype(float)

        for idx, current_df in enumerate(batch_dfs[1:], start=2):
            curr = current_df.copy()
            if "isPartial" in curr.columns:
                curr = curr.drop(columns=["isPartial"])

            if self.anchor_keyword not in curr.columns:
                self.logger.warning(f"Batch {idx} thiếu từ khóa mốc '{self.anchor_keyword}'. Bỏ qua chuẩn hóa batch này.")
                continue

            curr_anchor_series = curr[self.anchor_keyword].astype(float)

            # Tính hệ số tỉ lệ scale_factor dựa trên tỷ số giữa Anchor cơ sở và Anchor hiện tại
            # Chỉ xét các thời điểm Anchor > 0 để tránh chia cho 0
            valid_mask = (curr_anchor_series > 0) & (ref_anchor_series > 0)
            if valid_mask.sum() > 0:
                ratios = ref_anchor_series[valid_mask] / curr_anchor_series[valid_mask]
                # Dùng median ratio để loại bỏ nhiễu ngoại lai (robust against outliers)
                scale_factor = float(np.median(ratios))
            else:
                scale_factor = 1.0

            self.logger.info(f"Batch {idx}: Hệ số scale_factor so với anchor = {scale_factor:.4f}")

            # Áp dụng hệ số scale cho các cột mới trong current_df
            for col in curr.columns:
                if col != self.anchor_keyword and col not in master_df.columns:
                    master_df[col] = (curr[col].astype(float) * scale_factor).round(2)

        # Chuẩn hóa lại toàn bộ về thang đo tối đa 100 trên toàn bộ bảng
        numeric_cols = [c for c in master_df.columns if pd.api.types.is_numeric_dtype(master_df[c])]
        global_max = master_df[numeric_cols].values.max()
        if global_max > 0:
            master_df[numeric_cols] = ((master_df[numeric_cols] / global_max) * 100).round(2)

        return master_df

    def normalize_region_batches(
        self,
        batch_region_dfs: List[pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Gộp và chuẩn hóa dữ liệu theo 63 tỉnh/thành Việt Nam từ nhiều batch.
        """
        if not batch_region_dfs:
            return pd.DataFrame()

        base_df = batch_region_dfs[0].copy()
        for curr in batch_region_dfs[1:]:
            for col in curr.columns:
                if col not in ["geoCode", "geoName"] and col not in base_df.columns:
                    base_df[col] = curr[col]

        return base_df

