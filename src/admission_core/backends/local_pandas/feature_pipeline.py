"""Calendar-year lag features with prior-year Trends and forecast rows."""
from pathlib import Path
import numpy as np
import pandas as pd
from admission_core.ports import BaseFeaturePipelinePort
from admission_core.cdf_contract import CDFLookup
from admission_core.features import PROGRAM, KEYS, parse_blocks, major_mapping, major_join_keys, finish_features, validate_gold


class LocalPandasFeatureBackend(BaseFeaturePipelinePort):
    def build_features(self, input_data_uris, output_feature_uri, options=None):
        options = options or {}
        cutoff = pd.read_parquet(input_data_uris["cutoff_scores"])
        cutoff = cutoff.loc[cutoff.score_admission_name.eq("Điểm thi THPT")].copy()
        cutoff["score_year"] = pd.to_numeric(cutoff.score_year, errors="raise").astype(int)
        cutoff = cutoff.loc[cutoff.score_year.ge(int(options.get("min_label_year", 2016)))].copy()
        cutoff["score_mark"] = pd.to_numeric(cutoff.score_mark, errors="coerce")
        # Scores on a different scale require an explicit conversion, not clipping.
        cutoff = cutoff.loc[cutoff.score_mark.between(0, 30)].copy()
        if cutoff[["school_id", "school_name", "score_code", "score_year"]].isna().any().any():
            raise ValueError("Điểm chuẩn thiếu thông tin định danh")
        cutoff["school_id"] = cutoff.school_id.astype(str).str.strip()
        cutoff["score_code"] = cutoff.score_code.astype(str).str.strip()
        if cutoff.school_id.eq("").any() or cutoff.score_code.eq("").any():
            raise ValueError("Mã trường hoặc chương trình rỗng")
        cutoff["blocks"] = cutoff.score_blocks.map(parse_blocks)
        if cutoff.empty or cutoff.blocks.map(len).eq(0).any():
            raise ValueError("Điểm chuẩn rỗng hoặc không có tổ hợp được hỗ trợ")
        lookup = CDFLookup(pd.read_parquet(input_data_uris["cdf_data"]))
        cutoff["R_star"] = [np.mean([lookup.rank(row.score_year, block, row.score_mark)
                                     for block in row.blocks]) for row in cutoff.itertuples()]
        mapping = major_mapping(pd.read_parquet(input_data_uris["majors"]))
        cutoff = cutoff.merge(mapping, on=major_join_keys(mapping.columns), how="left", validate="many_to_one")
        if cutoff[["major_name", "major_group_name"]].isna().any().any():
            raise ValueError("Điểm chuẩn có mã ngành chưa được ánh xạ")
        programs = cutoff.groupby(PROGRAM, as_index=False).agg(
            R_star=("R_star", "mean"), blocks=("blocks", lambda lists: sorted(set(sum(lists, [])))))
        if programs.duplicated(KEYS).any():
            raise ValueError("Thông tin chương trình không nhất quán trong cùng năm")
        programs["allowed_blocks"] = programs.blocks.map(";".join)
        programs["num_blocks"] = programs.blocks.map(len)
        programs = programs.drop(columns="blocks")
        programs["offering_carried_forward"] = 0
        latest = int(programs.score_year.max())
        forecast_year = int(options.get("forecast_year", latest + 1))
        if forecast_year <= latest:
            raise ValueError("forecast_year phải lớn hơn năm điểm chuẩn cuối")
        future = programs.loc[programs.score_year.eq(latest)].copy()
        future["score_year"] = forecast_year
        future["R_star"] = np.nan
        future["offering_carried_forward"] = 1
        output = pd.concat([programs, future], ignore_index=True)
        lag = programs[KEYS + ["R_star"]].rename(columns={"R_star": "prog_pct_lag1"})
        lag["score_year"] += 1
        output = output.merge(lag, on=KEYS, how="left", validate="one_to_one")
        for key, columns in [
            ("school_id", {"school_pct_mean_lag1": "mean", "school_pct_min_lag1": "min"}),
            ("major_name", {"major_pct_mean_lag1": "mean"}),
            ("major_group_name", {"group_pct_mean_lag1": "mean"}),
        ]:
            aggregate = programs.groupby([key, "score_year"]).R_star.agg(**columns).reset_index()
            aggregate["score_year"] += 1
            output = output.merge(aggregate, on=[key, "score_year"], how="left", validate="many_to_one")
        annual_path = input_data_uris.get("trend_annual")
        keyword_path = input_data_uris.get("trend_keywords")
        if annual_path and keyword_path:
            annual = pd.read_parquet(annual_path)
            if annual.duplicated(["query_id", "year"]).any():
                raise ValueError("Trends theo năm trùng query_id và year")
            keywords = pd.read_parquet(keyword_path)[["query_id", "keyword", "keyword_type"]].drop_duplicates()
            trends = annual.merge(keywords, on="query_id")
            for kind, key, source, target in [
                ("school", "school_name", "interest_season_peak", "trend_school_peak"),
                ("major_group", "major_group_name", "interest_mean", "trend_group_mean"),
            ]:
                values = trends.loc[trends.keyword_type.eq(kind)].groupby(["keyword", "year"], as_index=False)[source].mean()
                values = values.rename(columns={"keyword": key, "year": "score_year", source: target})
                values["score_year"] = values.score_year.astype(int) + 1
                output = output.merge(values, on=[key, "score_year"], how="left", validate="many_to_one")
        else:
            output["trend_school_peak"] = 0.0
            output["trend_group_mean"] = 0.0
        output = finish_features(output)
        output = output.loc[output.score_year.ge(int(options.get("min_training_year", 2018)))].copy()
        validate_gold(output)
        Path(output_feature_uri).parent.mkdir(parents=True, exist_ok=True)
        output.sort_values(KEYS).to_parquet(output_feature_uri, index=False)
        return output_feature_uri
