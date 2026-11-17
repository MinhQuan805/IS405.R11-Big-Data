import pandas as pd
import pytest
import yaml
from admission_core.backends.apache_spark.session import SparkRuntime
from admission_core.backends.apache_spark.cdf import SparkCDFBackend
from admission_core.backends.apache_spark.feature_pipeline import SparkFeatureBackend
from admission_core.backends.local_pandas.cdf import LocalPandasCDFBackend
from admission_core.backends.local_pandas.feature_pipeline import LocalPandasFeatureBackend
from admission_core.cdf_contract import CDF_KEYS
from admission_core.features import KEYS

pytestmark = pytest.mark.spark


def test_spark_pandas_parity(demo_root, tmp_path):
    config = yaml.safe_load((demo_root / "apache_spark.yaml").read_text(encoding="utf-8"))
    sources = dict(config["data_ingestion"]["direct_sources"])
    cutoff = pd.read_parquet(sources["cutoff_scores"])
    earlier = cutoff.iloc[:1].copy()
    earlier["score_year"] = 2010
    pd.concat([cutoff, earlier], ignore_index=True).to_parquet(tmp_path / "cutoff.parquet", index=False)
    sources["cutoff_scores"] = str(tmp_path / "cutoff.parquet")
    catalog = pd.read_parquet(sources["majors"])
    contexts = cutoff.loc[cutoff.score_year.ge(2016), ["school_id", "score_year"]].drop_duplicates()
    catalog = catalog.merge(contexts, how="cross")
    catalog.loc[(catalog.school_id == "S0") & (catalog.score_codes == "M0"), "major_name"] = "Ngành riêng S0"
    catalog.to_parquet(tmp_path / "majors.parquet", index=False)
    sources["majors"] = str(tmp_path / "majors.parquet")
    keywords = pd.read_parquet(sources["trend_keywords"])
    alias = keywords.loc[keywords.keyword_type.eq("school")].iloc[:1].copy()
    alias["keyword"] = "Trường bí danh"
    pd.concat([keywords, alias], ignore_index=True).to_parquet(tmp_path / "keywords.parquet", index=False)
    sources["trend_keywords"] = str(tmp_path / "keywords.parquet")
    runtime = SparkRuntime(config["spark"])
    try:
        assert runtime.session.version == "4.3.0"
        for label, cdf_backend, feature_backend in [
            ("pandas", LocalPandasCDFBackend(), LocalPandasFeatureBackend()),
            ("spark", SparkCDFBackend(runtime), SparkFeatureBackend(runtime)),
        ]:
            cdf = cdf_backend.compute_cdf(sources, str(tmp_path / f"{label}_cdf.parquet"))
            feature_backend.build_features({**sources, "cdf_data": cdf}, str(tmp_path / f"{label}_gold.parquet"))
        for suffix, keys in [("cdf", CDF_KEYS), ("gold", KEYS)]:
            frames = [pd.read_parquet(tmp_path / f"{label}_{suffix}.parquet").sort_values(keys).reset_index(drop=True).sort_index(axis=1)
                      for label in ("pandas", "spark")]
            pd.testing.assert_frame_equal(*frames, check_dtype=False, atol=1e-8, rtol=1e-8)
    finally:
        runtime.close()


def test_original_sources_invalid_values_and_ties(tmp_path):
    first = tmp_path / "ct2006.parquet"
    second = tmp_path / "ct2018.parquet"
    pd.DataFrame({"Nam": ["20-2", "20-2", "invalid", "25", "25"],
                  "KhoiA": ["20", "20", "25", "invalid", "25"]}).to_parquet(first, index=False)
    pd.DataFrame({"KhoiA": [20.0, 30.0, float("nan"), float("inf")]}).to_parquet(second, index=False)
    sources = {"score_distribution_ct2006": str(first), "score_distribution_ct2018": str(second)}
    runtime = SparkRuntime()
    try:
        paths = [LocalPandasCDFBackend().compute_cdf(sources, str(tmp_path / "expected.parquet")),
                 SparkCDFBackend(runtime).compute_cdf(sources, str(tmp_path / "actual.parquet"))]
        frames = [pd.read_parquet(path).sort_values(CDF_KEYS).reset_index(drop=True) for path in paths]
        pd.testing.assert_frame_equal(*frames, check_dtype=False, atol=1e-8)
        from admission_core.cdf_contract import CDFLookup
        lookup = CDFLookup(frames[1])
        assert lookup.rank(2020, "A00", 20) == 0
        assert lookup.rank(2025, "A00", 20) == pytest.approx(2 / 3)
        options = {"excluded_year_labels": {"score_distribution_ct2006": ["20-2"]}}
        filtered = [LocalPandasCDFBackend().compute_cdf(sources, str(tmp_path / "filtered_pandas.parquet"), options),
                    SparkCDFBackend(runtime).compute_cdf(sources, str(tmp_path / "filtered_spark.parquet"), options)]
        frames = [pd.read_parquet(path).sort_values(CDF_KEYS).reset_index(drop=True) for path in filtered]
        pd.testing.assert_frame_equal(*frames, check_dtype=False, atol=1e-8)
        assert not frames[0].score_year.eq(2020).any()
    finally:
        runtime.close()
