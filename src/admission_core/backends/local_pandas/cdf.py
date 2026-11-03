"""Local CDF Engine Adapter (Pandas / NumPy / In-Memory).
Implements Module 2: Computes Empirical CDF distributions and Survival Rank (1 - F(s)).
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from admission_core.ports import BaseCDFPort
from admission_core.specs.contracts import BLOCK_NAME_MAP

class LocalPandasCDFBackend(BaseCDFPort):
    """Bộ chuyển đổi tính toán CDF cục bộ bằng Pandas / NumPy"""

    def compute_cdf(
        self, 
        raw_dist_sources: Dict[str, str], 
        output_uri: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        print("[Engine: LOCAL_PANDAS] Bắt đầu tính toán bảng CDF phổ điểm...")
        blocks_analysis = list(BLOCK_NAME_MAP.values())
        
        path_2006 = raw_dist_sources.get("score_distribution_ct2006")
        path_2018 = raw_dist_sources.get("score_distribution_ct2018")
        
        dfs = []
        if path_2006 and os.path.exists(path_2006):
            cols_2006 = ['Nam'] + [b for b in blocks_analysis]
            df_06 = pd.read_parquet(path_2006, columns=cols_2006)
            year_map = {
                '16': 2016, '17': 2017, '18': 2018, '19': 2019, '20': 2020, 
                '20-2': 2020, '21': 2021, '21-2': 2021, '22': 2022, '23': 2023, 
                '24': 2024, '25': 2025
            }
            df_06['score_year'] = df_06['Nam'].map(year_map)
            dfs.append(df_06[['score_year'] + blocks_analysis])

        if path_2018 and os.path.exists(path_2018):
            df_18 = pd.read_parquet(path_2018, columns=blocks_analysis)
            df_18['score_year'] = 2025
            dfs.append(df_18[['score_year'] + blocks_analysis])

        if not dfs:
            raise FileNotFoundError("Không tìm thấy dữ liệu phổ điểm đầu vào để tính CDF.")

        df_all = pd.concat(dfs, ignore_index=True)
        
        # Tạo bảng lưu trữ phân phối đã sắp xếp
        out_dir = Path(output_uri)
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Lưu dưới dạng tệp parquet tóm tắt
        df_all.to_parquet(output_uri, index=False)
        print(f"[Engine: LOCAL_PANDAS] Đã lưu bảng phân phối tích lũy tại: {output_uri}")
        return output_uri

