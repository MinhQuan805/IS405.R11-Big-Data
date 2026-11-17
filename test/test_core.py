import json
import math
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml
from admission_core.cdf_contract import CDFLookup, normalize_scores, summarize_scores
from admission_core.specs.math_formulas import calculate_admission_probability, classify_decision_tier
from admission_core.validation.quality_gate import QualityGate
from admission_core.factory import get_cdf_backend, get_feature_backend
from admission_core.pipeline import AdmissionPipeline


def test_cdf_ties_and_boundaries():
    observations = pd.DataFrame({"score_year": [2025] * 4, "block_name": ["KhoiA"] * 4,
                                 "score_value": [20.0, 20, 25, 30]})
    lookup = CDFLookup(summarize_scores(observations))
    assert lookup.rank(2025, "A00", 20) == 0.5
    assert lookup.rank(2025, "A00", 24.99) == 0.5
    assert lookup.rank(2025, "A00", 25) == 0.25
    assert lookup.rank(2025, "A00", 0) == 1
    assert lookup.rank(2025, "A00", 30) == 0
    with pytest.raises(ValueError):
        lookup.rank(2026, "A00", 20)


def test_normalize_invalid_and_original_years():
    values = pd.DataFrame({"Nam": ["20-2", "21-2", "invalid", "25", "25"],
                           "KhoiA": [20, 21, 20, float("nan"), float("inf")]})
    output = normalize_scores(values, "score_distribution_ct2006")
    assert output.score_year.tolist() == [2020, 2021]


def test_math_monotonicity():
    probabilities = [calculate_admission_probability(rank, 0.2, 0.01) for rank in (0.1, 0.2, 0.3)]
    assert probabilities[0] > probabilities[1] > probabilities[2]
    assert probabilities[1] == 0.5
    assert classify_decision_tier(0.8).startswith("An toàn")
    assert classify_decision_tier(0.5).startswith("Cạnh tranh")


@pytest.mark.parametrize("variance", [-1, float("nan"), float("inf")])
def test_math_rejects_invalid_variance(variance):
    with pytest.raises(ValueError):
        calculate_admission_probability(0.2, 0.2, variance)


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -0.1])
def test_gate_rejects_invalid(value):
    assert not QualityGate().validate({"rmse": value, "mse": 0.02, "r2": 0.9})[0]


def test_gate_boundary():
    assert QualityGate().validate({"rmse": 0.16, "mse": 0.0256, "r2": 0.78})[0]
    assert not QualityGate().validate({"rmse": 0.17, "mse": 0.0289, "r2": 0.78})[0]


def test_factory():
    assert get_cdf_backend({"execution_backend": "apache_spark"}).__class__.__name__ == "SparkCDFBackend"
    assert get_feature_backend({"execution_backend": "local_pandas"}).__class__.__name__ == "LocalPandasFeatureBackend"
    with pytest.raises(ValueError):
        get_cdf_backend({"execution_backend": "duckdb"})


def test_plugins(tmp_path):
    source = tmp_path / "long.parquet"
    pd.DataFrame({"score_year": [2025] * 4, "block_name": ["KhoiA"] * 4,
                  "score_value": [20.0, 20, 25, 30]}).to_parquet(source)
    sources = {"score_distribution_ct2006": str(source)}
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    configs = [
        {"type": "class_adapter", "target": "plugins.custom_cdf_adapter.CustomUserCDFAdapter"},
        {"type": "external_script", "command": ["{python}", str(root / "plugins/custom_script_cdf.py"),
                                                "--input", "{input_uri}", "--output", "{output_uri}"]},
    ]
    for index, config in enumerate(configs):
        adapter = get_cdf_backend({"backend_execution": {"cdf_stage": config}})
        output = adapter.compute_cdf(sources, str(tmp_path / f"result{index}.parquet"))
        assert CDFLookup(pd.read_parquet(output)).rank(2025, "A00", 20) == 0.5


def test_plugin_failure(tmp_path):
    adapter = get_cdf_backend({"backend_execution": {"cdf_stage": {
        "type": "external_script", "command": ["{python}", "-c", "raise SystemExit(2)"]}}})
    import subprocess
    with pytest.raises(subprocess.CalledProcessError):
        adapter.compute_cdf({}, str(tmp_path / "missing.parquet"))


def test_failed_candidate_preserves_current(tmp_path, monkeypatch):
    root = tmp_path / "models"
    root.mkdir()
    pointer = root / "current.json"
    pointer.write_text('{"version":"old"}', encoding="utf-8")
    original = pointer.read_bytes()
    pipeline = AdmissionPipeline({"data_paths": {"models_dir": str(root)}})
    def bad_model(*args, **kwargs):
        return {"rmse": 1.0, "mse": 1.0, "r2": -1.0}
    monkeypatch.setattr(pipeline.trainer_backend, "train_and_evaluate", bad_model)
    with pytest.raises(RuntimeError):
        pipeline.train("unused", "unused")
    assert pointer.read_bytes() == original


def test_calendar_lag_and_future_invariance(demo_root, tmp_path):
    from admission_core.backends.local_pandas.cdf import LocalPandasCDFBackend
    from admission_core.backends.local_pandas.feature_pipeline import LocalPandasFeatureBackend
    sources = yaml.safe_load((demo_root / "local_pandas.yaml").read_text(encoding="utf-8"))["data_ingestion"]["direct_sources"]
    sources = dict(sources)
    cdf = LocalPandasCDFBackend().compute_cdf(sources, str(tmp_path / "cdf.parquet"))
    cutoff = pd.read_parquet(sources["cutoff_scores"])
    earlier = cutoff.iloc[:1].copy()
    earlier["score_year"] = 2010
    cutoff = pd.concat([cutoff, earlier], ignore_index=True)
    cutoff = cutoff.loc[~((cutoff.school_id == "S0") & (cutoff.score_code == "M0") & (cutoff.score_year == 2020))]
    source = tmp_path / "cutoff.parquet"
    cutoff.to_parquet(source, index=False)
    sources.update(cutoff_scores=str(source), cdf_data=cdf)
    backend = LocalPandasFeatureBackend()
    backend.build_features(sources, str(tmp_path / "gold.parquet"))
    gold = pd.read_parquet(tmp_path / "gold.parquet")
    row = gold.loc[(gold.school_id == "S0") & (gold.score_code == "M0") & (gold.score_year == 2021)].iloc[0]
    assert row.is_new_program == 1
    assert row.prog_pct_lag1 == pytest.approx((row.school_pct_mean_lag1 + row.major_pct_mean_lag1) / 2)
    cutoff.loc[cutoff.score_year == 2025, "score_mark"] = 29
    cutoff.to_parquet(source, index=False)
    backend.build_features(sources, str(tmp_path / "changed.parquet"))
    changed = pd.read_parquet(tmp_path / "changed.parquet")
    columns = ["school_id", "score_code", "score_year"]
    left = gold.loc[gold.score_year <= 2024].sort_values(columns).reset_index(drop=True)
    right = changed.loc[changed.score_year <= 2024].sort_values(columns).reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)


def test_training_is_out_of_time(trained_root):
    from admission_core.artifacts import resolve_release
    metadata = json.loads((resolve_release(trained_root) / "model_metadata.json").read_text(encoding="utf-8"))
    assert "is_cutoff_over_30" not in metadata["features"]
    for fold in metadata["performance_metrics"]["folds"]:
        assert fold["train_max_year"] < fold["test_year"]


def test_trainer_error_preserves_current(tmp_path, monkeypatch):
    root = tmp_path / "models"
    root.mkdir()
    pointer = root / "current.json"
    pointer.write_text('{"version":"old"}', encoding="utf-8")
    original = pointer.read_bytes()
    pipeline = AdmissionPipeline({"data_paths": {"models_dir": str(root)}})
    def interrupted_training(*args, **kwargs):
        raise RuntimeError("training interrupted")
    monkeypatch.setattr(pipeline.trainer_backend, "train_and_evaluate", interrupted_training)
    with pytest.raises(RuntimeError, match="training interrupted"):
        pipeline.train("unused", "unused")
    assert pointer.read_bytes() == original


def test_artifact_checksum(trained_root, tmp_path):
    import shutil
    from admission_core.artifacts import resolve_release
    from admission_core.inference import AdmissionPredictor
    copied = tmp_path / "models"
    shutil.copytree(trained_root, copied)
    release = resolve_release(copied)
    with (release / "best_lightgbm_regressor.joblib").open("ab") as stream:
        stream.write(b"corrupted")
    with pytest.raises(ValueError, match="toàn vẹn"):
        AdmissionPredictor(copied)


def test_major_mapping_ignores_missing_codes():
    from admission_core.features import major_mapping
    frame = pd.DataFrame({"score_codes": ["M0", None, None], "major_name": ["A", "B", "C"],
                          "major_group_name": ["G", "G", "H"]})
    assert major_mapping(frame).score_code.tolist() == ["M0"]


def test_cdf_excludes_only_configured_duplicate_round(tmp_path):
    from admission_core.backends.local_pandas.cdf import LocalPandasCDFBackend
    source = tmp_path / "scores.parquet"
    pd.DataFrame({"Nam": ["20", "20-2", "21-2"], "KhoiA": [20.0, 20.0, 25.0]}).to_parquet(source)
    options = {"excluded_year_labels": {"score_distribution_ct2006": ["20-2"]}}
    output = LocalPandasCDFBackend().compute_cdf({"score_distribution_ct2006": str(source)},
        str(tmp_path / "cdf.parquet"), options)
    frame = pd.read_parquet(output)
    assert frame.loc[frame.score_year.eq(2020), "total_candidates"].iloc[0] == 1
    assert frame.loc[frame.score_year.eq(2021), "total_candidates"].iloc[0] == 1
