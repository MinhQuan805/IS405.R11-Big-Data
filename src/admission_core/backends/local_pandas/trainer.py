"""Local Model Trainer Backend (LightGBM Point + Quantiles).
Trains and evaluates models according to Module 3 probabilistic framework.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import spearmanr

from admission_core.ports import BaseTrainerPort
from admission_core.specs.contracts import (
    OFFICIAL_FEATURES, TARGET_FEATURE, BAYES_ERROR_FLOOR_MSE
)

class LocalLightGBMTrainerBackend(BaseTrainerPort):
    """Bộ chuyển đổi huấn luyện mô hình LightGBM cục bộ"""

    def train_and_evaluate(
        self, 
        feature_matrix_uri: str, 
        output_model_dir: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        print("[Engine: LOCAL_TRAINER] Bắt đầu huấn luyện mô hình LightGBM...")
        df = pd.read_parquet(feature_matrix_uri)
        
        X = df[OFFICIAL_FEATURES].fillna(0.0).values
        y = df[TARGET_FEATURE].values
        
        opts = options or {}
        hp = opts.get("hyperparameters", {
            "learning_rate": 0.07,
            "max_depth": 8,
            "num_leaves": 45,
            "n_estimators": 180,
            "subsample": 0.95,
            "colsample_bytree": 0.95,
            "reg_alpha": 1.0,
            "reg_lambda": 1.0,
            "random_state": 42,
            "verbose": -1,
            "n_jobs": -1
        })
        
        # 1. 5-Fold Cross Validation
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        mse_list, mae_list, r2_list, spearman_list = [], [], [], []
        
        for train_idx, val_idx in kf.split(X, y):
            X_tr, y_tr = X[train_idx], y[train_idx]
            X_val, y_val = X[val_idx], y[val_idx]
            
            m = lgb.LGBMRegressor(**hp)
            m.fit(X_tr, y_tr)
            preds = m.predict(X_val)
            
            mse_list.append(mean_squared_error(y_val, preds))
            mae_list.append(mean_absolute_error(y_val, preds))
            r2_list.append(r2_score(y_val, preds))
            rho, _ = spearmanr(y_val, preds)
            spearman_list.append(rho)

        metrics = {
            "5fold_cv_mse": float(np.mean(mse_list)),
            "5fold_cv_rmse": float(np.sqrt(np.mean(mse_list))),
            "5fold_cv_mae": float(np.mean(mae_list)),
            "5fold_cv_r2": float(np.mean(r2_list)),
            "5fold_cv_spearman_rho": float(np.mean(spearman_list)),
            "bayes_error_floor_mse": BAYES_ERROR_FLOOR_MSE,
            "training_samples": len(df),
            "training_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 2. Huấn luyện Point Regressor trên toàn bộ tập dữ liệu
        best_lgb = lgb.LGBMRegressor(**hp)
        best_lgb.fit(X, y)
        
        # 3. Huấn luyện 3 mô hình Quantile
        quantiles = opts.get("quantiles", [0.1, 0.5, 0.9])
        quantile_models = {}
        for q in quantiles:
            q_hp = hp.copy()
            q_hp["objective"] = "quantile"
            q_hp["alpha"] = q
            qm = lgb.LGBMRegressor(**q_hp)
            qm.fit(X, y)
            quantile_models[q] = qm

        # 4. Xuất mô hình ra thư mục đích
        out_dir = Path(output_model_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(best_lgb, out_dir / "best_lightgbm_regressor.joblib")
        for q, qm in quantile_models.items():
            joblib.dump(qm, out_dir / f"lightgbm_quantile_{q}.joblib")

        metadata = {
            "model_name": "LightGBM Admission Percentile Regressor",
            "training_date": metrics["training_date"],
            "training_samples": metrics["training_samples"],
            "features": OFFICIAL_FEATURES,
            "best_hyperparameters": hp,
            "performance_metrics": metrics,
            "model_files": {
                "point_estimator": "best_lightgbm_regressor.joblib",
                "quantile_0.1": "lightgbm_quantile_0.1.joblib",
                "quantile_0.5": "lightgbm_quantile_0.5.joblib",
                "quantile_0.9": "lightgbm_quantile_0.9.joblib"
            }
        }
        with open(out_dir / "model_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        print(f"[Engine: LOCAL_TRAINER] Huấn luyện thành công! RMSE={metrics['5fold_cv_rmse']:.4f}, R2={metrics['5fold_cv_r2']:.4f}")
        return metrics

