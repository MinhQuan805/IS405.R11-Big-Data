"""LightGBM point and quantile models evaluated with expanding-year folds."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from scipy.stats import spearmanr
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, mean_pinball_loss
from admission_core.ports import BaseTrainerPort
from admission_core.features import LOOKUP_COLUMNS, validate_gold
from admission_core.specs.contracts import OFFICIAL_FEATURES, FEATURE_SCHEMA_VERSION


class LocalLightGBMTrainerBackend(BaseTrainerPort):
    def train_and_evaluate(self, feature_matrix_uri, output_model_dir, options=None):
        options = options or {}
        dataset = ds.dataset(feature_matrix_uri, format="parquet")
        if dataset.count_rows() > int(options.get("max_gold_rows", 1_000_000)):
            raise ValueError("Gold vượt giới hạn huấn luyện cục bộ")
        frame = validate_gold(dataset.to_table().to_pandas())
        labeled = frame.loc[frame.R_star.notna()].sort_values(["score_year", "school_id", "score_code"])
        years = sorted(labeled.score_year.unique())
        min_years = int(options.get("min_train_years", 2))
        if min_years < 1 or len(years) <= min_years:
            raise ValueError("Không đủ năm để kiểm định theo thời gian")
        hp = {"n_estimators": 180, "learning_rate": 0.07, "num_leaves": 31,
              "random_state": 42, "n_jobs": 2, "verbosity": -1}
        hp.update(options.get("hyperparameters", {}))
        if hp.get("objective", "regression") != "regression":
            raise ValueError("Point model yêu cầu objective regression")
        quantiles = [0.1, 0.5, 0.9]
        folds, predictions = [], []
        for year in years[min_years:]:
            train = labeled.loc[labeled.score_year.lt(year)]
            valid = labeled.loc[labeled.score_year.eq(year)]
            if len(valid) < 2:
                raise ValueError("Mỗi năm kiểm định cần ít nhất hai chương trình")
            model = lgb.LGBMRegressor(**hp).fit(train[OFFICIAL_FEATURES], train.R_star)
            point = np.clip(model.predict(valid[OFFICIAL_FEATURES]), 0, 1)
            quantile_predictions = []
            losses = {}
            for quantile in quantiles:
                params = dict(hp, objective="quantile", alpha=quantile)
                fitted = lgb.LGBMRegressor(**params).fit(train[OFFICIAL_FEATURES], train.R_star)
                predicted = np.clip(fitted.predict(valid[OFFICIAL_FEATURES]), 0, 1)
                quantile_predictions.append(predicted)
                losses[str(quantile)] = float(mean_pinball_loss(valid.R_star, predicted, alpha=quantile))
            raw_quantiles = np.column_stack(quantile_predictions)
            ordered = np.sort(raw_quantiles, axis=1)
            fold = {"test_year": int(year), "train_max_year": int(train.score_year.max()),
                    "train_samples": len(train), "test_samples": len(valid),
                    "rmse": float(np.sqrt(mean_squared_error(valid.R_star, point))),
                    "r2": float(r2_score(valid.R_star, point)), "pinball_loss": losses,
                    "coverage_80": float(np.mean((valid.R_star >= ordered[:, 0]) & (valid.R_star <= ordered[:, 2]))),
                    "interval_width": float(np.mean(ordered[:, 2] - ordered[:, 0])),
                    "crossing_rate": float(np.mean(np.any(np.diff(raw_quantiles, axis=1) < 0, axis=1)))}
            folds.append(fold)
            prediction = valid[["school_id", "score_code", "score_year", "R_star", "is_new_program"]].copy()
            prediction["prediction"] = point
            prediction["baseline"] = valid.prog_pct_lag1.to_numpy()
            for index, quantile in enumerate(quantiles):
                prediction[f"q{quantile}"] = ordered[:, index]
            predictions.append(prediction)
        oof = pd.concat(predictions, ignore_index=True)
        rho = spearmanr(oof.R_star, oof.prediction).statistic
        metrics = {
            "evaluation_method": "expanding_year", "rmse": float(np.sqrt(mean_squared_error(oof.R_star, oof.prediction))),
            "mse": float(mean_squared_error(oof.R_star, oof.prediction)),
            "mae": float(mean_absolute_error(oof.R_star, oof.prediction)),
            "r2": float(r2_score(oof.R_star, oof.prediction)),
            "spearman_rho": float(rho) if np.isfinite(rho) else None,
            "baseline_rmse": float(np.sqrt(mean_squared_error(oof.R_star, oof.baseline))),
            "coverage_80": float(np.mean((oof.R_star >= oof["q0.1"]) & (oof.R_star <= oof["q0.9"]))),
            "training_samples": len(labeled), "evaluation_samples": len(oof), "folds": folds,
            "training_date": datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
            "subgroups": {},
        }
        for flag, group in oof.groupby("is_new_program"):
            metrics["subgroups"]["new" if flag else "existing"] = {
                "samples": len(group), "rmse": float(np.sqrt(mean_squared_error(group.R_star, group.prediction)))}
        output = Path(output_model_dir)
        output.mkdir(parents=True, exist_ok=True)
        filenames = {"point_estimator": "best_lightgbm_regressor.joblib"}
        model = lgb.LGBMRegressor(**hp).fit(labeled[OFFICIAL_FEATURES], labeled.R_star)
        joblib.dump(model, output / filenames["point_estimator"])
        for quantile in quantiles:
            model = lgb.LGBMRegressor(**dict(hp, objective="quantile", alpha=quantile))
            model.fit(labeled[OFFICIAL_FEATURES], labeled.R_star)
            filename = f"lightgbm_quantile_{quantile}.joblib"
            joblib.dump(model, output / filename)
            filenames[f"quantile_{quantile}"] = filename
        future = frame.loc[frame.score_year.gt(max(years)), LOOKUP_COLUMNS]
        if future.empty:
            raise ValueError("Thiếu đặc trưng cho năm dự báo sau năm huấn luyện cuối")
        future.to_parquet(output / "serving_features.parquet", index=False)
        oof.to_parquet(output / "out_of_time_predictions.parquet", index=False)
        metadata = {"feature_schema_version": FEATURE_SCHEMA_VERSION, "features": OFFICIAL_FEATURES,
                    "training_data_kind": options.get("data_kind", "unspecified"),
                    "training_max_year": int(max(years)), "forecast_years": sorted(map(int, future.score_year.unique())),
                    "hyperparameters": hp, "performance_metrics": metrics, "model_files": filenames,
                    "trends_policy": "previous_calendar_year", "cdf_policy": "strictly_greater_step_cdf"}
        (output / "model_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        return metrics
