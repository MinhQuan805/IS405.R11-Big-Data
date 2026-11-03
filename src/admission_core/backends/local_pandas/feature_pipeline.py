"""Local Feature Pipeline Backend (Pandas / NumPy).
Builds the gold hierarchical lag matrix, Trends signals, and 4 polynomial interactions.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from admission_core.ports import BaseFeaturePipelinePort
from admission_core.specs.contracts import OFFICIAL_FEATURES, TARGET_FEATURE, BLOCK_NAME_MAP

class LocalPandasFeatureBackend(BaseFeaturePipelinePort):
    """Bộ chuyển đổi trích xuất đặc trưng đa tầng cục bộ"""

    def build_features(
        self, 
        input_data_uris: Dict[str, str], 
        output_feature_uri: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        print("[Engine: LOCAL_PANDAS] Đang xây dựng ma trận đặc trưng nòng cốt...")
        
        path_cutoff = input_data_uris["cutoff_scores"]
        path_majors = input_data_uris["majors"]
        path_annual = input_data_uris.get("trend_annual")
        path_keywords = input_data_uris.get("trend_keywords")
        path_cdf = input_data_uris["cdf_data"]

        df_cutoff = pd.read_parquet(path_cutoff)
        df_majors = pd.read_parquet(path_majors)
        df_dist_all = pd.read_parquet(path_cdf)

        # Lọc phương thức xét tuyển THPT
        df_thpt = df_cutoff[
            (df_cutoff['score_admission_name'] == 'Điểm thi THPT') &
            (df_cutoff['score_year'] >= 2016) &
            (df_cutoff['score_year'] <= 2025)
        ].copy()

        blocks_analysis = list(BLOCK_NAME_MAP.values())
        cdf_dict = {}
        for y in range(2016, 2026):
            sub_y = df_dist_all[df_dist_all['score_year'] == y]
            for b in blocks_analysis:
                arr = np.sort(sub_y[b].dropna().values)
                if len(arr) > 0:
                    cdf_dict[(y, b)] = arr

        avg_year_dist = {}
        for y in range(2016, 2026):
            cands = [cdf_dict[(y, b)] for b in ['KhoiA', 'KhoiA1', 'KhoiD'] if (y, b) in cdf_dict and len(cdf_dict[(y, b)]) > 0]
            avg_year_dist[y] = np.concatenate(cands) if cands else None

        # 1. Tính toán R_star
        def _compute_r_star(row):
            y = row['score_year']
            c = min(float(row['score_mark']), 30.0)
            b_str = row['score_blocks']
            recognized = []
            if isinstance(b_str, str):
                for part in b_str.split(';'):
                    p = part.strip()
                    if p in BLOCK_NAME_MAP and (y, BLOCK_NAME_MAP[p]) in cdf_dict:
                        recognized.append(BLOCK_NAME_MAP[p])
            if recognized:
                pcts = [1.0 - (np.searchsorted(cdf_dict[(y, col)], c, side='right') / len(cdf_dict[(y, col)])) for col in recognized]
                return float(np.mean(pcts))
            else:
                if y in avg_year_dist and avg_year_dist[y] is not None:
                    return float(1.0 - (np.searchsorted(avg_year_dist[y], c, side='right') / len(avg_year_dist[y])))
                return 0.5

        df_thpt['R_star'] = df_thpt.apply(_compute_r_star, axis=1)
        df_thpt['num_blocks'] = df_thpt['score_blocks'].apply(
            lambda s: len([p for p in s.split(';') if p.strip()]) if isinstance(s, str) and s.strip() else 1
        )
        df_thpt['is_cutoff_over_30'] = (df_thpt['score_mark'] > 30.0).astype(int)

        # 2. Merge danh mục ngành
        df_exploded = df_majors.assign(score_code=df_majors['score_codes'].str.split(';')).explode('score_code')
        df_exploded['score_code'] = df_exploded['score_code'].str.strip()
        df_code_map = df_exploded[df_exploded['score_code'] != ''].drop_duplicates(subset=['score_code'])
        df_merged = df_thpt.merge(df_code_map[['score_code', 'major_id', 'major_name', 'major_group_id', 'major_group_name']], on='score_code', how='left')

        prog_df = df_merged.groupby(['school_id', 'school_name', 'score_code', 'major_name', 'major_group_name', 'score_year']).agg(
            R_star=('R_star', 'mean'), 
            score_mark=('score_mark', 'mean'), 
            num_blocks=('num_blocks', 'first'), 
            is_cutoff_over_30=('is_cutoff_over_30', 'max')
        ).reset_index()

        # 3. Tạo trễ và làm mượt đa tầng
        prog_lags = prog_df[['school_id', 'score_code', 'score_year', 'R_star']].copy()
        for l in [1, 2, 3]:
            pl = prog_lags.copy()
            pl['score_year'] = pl['score_year'] + l
            pl = pl.rename(columns={'R_star': f'prog_pct_lag{l}'})
            prog_df = prog_df.merge(pl, on=['school_id', 'score_code', 'score_year'], how='left')

        # Trường
        school_agg = prog_df.groupby(['school_id', 'score_year'])['R_star'].agg(
            school_pct_mean='mean', school_pct_med='median', school_pct_min='min', school_pct_max='max', school_pct_std='std'
        ).reset_index().fillna(0)
        for l in [1, 2]:
            sl = school_agg.copy()
            sl['score_year'] = sl['score_year'] + l
            sl.columns = ['school_id', 'score_year'] + [f'{c}_lag{l}' for c in sl.columns if c not in ['school_id', 'score_year']]
            prog_df = prog_df.merge(sl, on=['school_id', 'score_year'], how='left')

        # Ngành
        major_agg = prog_df.groupby(['major_name', 'score_year'])['R_star'].agg(
            major_pct_mean='mean', major_pct_med='median', major_pct_std='std'
        ).reset_index().fillna(0)
        for l in [1, 2]:
            ml = major_agg.copy()
            ml['score_year'] = ml['score_year'] + l
            ml.columns = ['major_name', 'score_year'] + [f'{c}_lag{l}' for c in ml.columns if c not in ['major_name', 'score_year']]
            prog_df = prog_df.merge(ml, on=['major_name', 'score_year'], how='left')

        # Nhóm ngành
        group_agg = prog_df.groupby(['major_group_name', 'score_year'])['R_star'].agg(
            group_pct_mean='mean', group_pct_med='median', group_pct_std='std'
        ).reset_index().fillna(0)
        gl = group_agg.copy()
        gl['score_year'] = gl['score_year'] + 1
        gl.columns = ['major_group_name', 'score_year'] + [f'{c}_lag1' for c in gl.columns if c not in ['major_group_name', 'score_year']]
        prog_df = prog_df.merge(gl, on=['major_group_name', 'score_year'], how='left')

        # 4. Tín hiệu Trends
        if path_annual and path_keywords and Path(path_annual).exists() and Path(path_keywords).exists():
            df_annual = pd.read_parquet(path_annual)
            df_keywords = pd.read_parquet(path_keywords)
            df_trends_merged = df_annual.merge(df_keywords[['query_id', 'keyword', 'keyword_type']], on='query_id', how='inner')
            s_trend = df_trends_merged[df_trends_merged['keyword_type'] == 'school'].groupby(['keyword', 'year']).agg(
                trend_school_mean=('interest_mean', 'mean'), trend_school_peak=('interest_season_peak', 'mean')
            ).reset_index().rename(columns={'keyword': 'school_name', 'year': 'score_year'})
            g_trend = df_trends_merged[df_trends_merged['keyword_type'] == 'major_group'].groupby(['keyword', 'year']).agg(
                trend_group_mean=('interest_mean', 'mean')
            ).reset_index().rename(columns={'keyword': 'major_group_name', 'year': 'score_year'})

            prog_df = prog_df.merge(s_trend, on=['school_name', 'score_year'], how='left')
            prog_df = prog_df.merge(g_trend, on=['major_group_name', 'score_year'], how='left')
        else:
            prog_df['trend_school_peak'] = 0.0
            prog_df['trend_group_mean'] = 0.0

        # Lọc giai đoạn huấn luyện (2018 - 2025)
        model_df = prog_df[prog_df['score_year'] >= 2018].copy()

        # Điền missing và khởi đầu lạnh
        num_lag_cols = [c for c in model_df.columns if c.startswith(('school_pct', 'major_pct', 'group_pct'))]
        for c in num_lag_cols:
            model_df[c] = model_df[c].fillna(model_df[c].median()).fillna(0.5)

        model_df['is_new_program'] = model_df['prog_pct_lag1'].isna().astype(int)
        model_df['prog_pct_lag1'] = model_df['prog_pct_lag1'].fillna(
            0.5 * model_df['school_pct_mean_lag1'] + 0.5 * model_df['major_pct_mean_lag1']
        ).fillna(0.5)

        model_df['delta_prog_vs_school_mean'] = model_df['prog_pct_lag1'] - model_df['school_pct_mean_lag1']
        model_df['delta_prog_vs_major_mean'] = model_df['prog_pct_lag1'] - model_df['major_pct_mean_lag1']
        model_df['trend_school_peak'] = model_df['trend_school_peak'].fillna(0.0)
        model_df['trend_group_mean'] = model_df['trend_group_mean'].fillna(0.0)

        # 4 biến tương tác bậc 2
        model_df['inter_prog_school'] = model_df['prog_pct_lag1'] * model_df['school_pct_mean_lag1']
        model_df['inter_school_major'] = model_df['school_pct_mean_lag1'] * model_df['major_pct_mean_lag1']
        model_df['inter_prog_blocks'] = model_df['prog_pct_lag1'] * model_df['num_blocks']
        model_df['inter_school_blocks'] = model_df['school_pct_mean_lag1'] * model_df['num_blocks']

        cols_to_save = ['school_id', 'school_name', 'score_code', 'major_name', 'score_year', TARGET_FEATURE] + OFFICIAL_FEATURES
        out_df = model_df[[c for c in cols_to_save if c in model_df.columns]].copy()
        
        Path(output_feature_uri).parent.mkdir(parents=True, exist_ok=True)
        out_df.to_parquet(output_feature_uri, index=False)
        print(f"[Engine: LOCAL_PANDAS] Đã trích xuất ma trận {len(out_df)} dòng x {len(OFFICIAL_FEATURES)} đặc trưng tại: {output_feature_uri}")
        return output_feature_uri

