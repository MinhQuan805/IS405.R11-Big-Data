"""Load an immutable release and infer admission probabilities from real artifacts."""
import json
import math
from pathlib import Path
from time import perf_counter
import joblib
import numpy as np
import pandas as pd
from admission_core.artifacts import resolve_release
from admission_core.cdf_contract import CDFLookup
from admission_core.features import KEYS, LOOKUP_COLUMNS
from admission_core.specs.contracts import OFFICIAL_FEATURES, FEATURE_SCHEMA_VERSION, BLOCK_NAME_MAP
from admission_core.specs.math_formulas import calculate_admission_probability, classify_decision_tier


class PredictionError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


class AdmissionPredictor:
    def __init__(self, model_root):
        self.release = resolve_release(model_root)
        self.metadata = json.loads((self.release / "model_metadata.json").read_text(encoding="utf-8"))
        if self.metadata.get("feature_schema_version") != FEATURE_SCHEMA_VERSION or self.metadata.get("features") != OFFICIAL_FEATURES:
            raise ValueError("Model dùng contract cũ hoặc không tương thích. Cần huấn luyện lại")
        self.models = {name: joblib.load(self.release / filename)
                       for name, filename in self.metadata["model_files"].items()}
        required = {"point_estimator", "quantile_0.1", "quantile_0.5", "quantile_0.9"}
        if set(self.models) != required:
            raise ValueError("Bộ model không đầy đủ")
        for model in self.models.values():
            if model.n_features_in_ != len(OFFICIAL_FEATURES):
                raise ValueError("Số đặc trưng của model không khớp metadata")
        features = pd.read_parquet(self.release / "serving_features.parquet")
        if features.empty or set(LOOKUP_COLUMNS) - set(features.columns) or features.duplicated(KEYS).any():
            raise ValueError("Feature lookup thiếu cột, rỗng hoặc trùng khóa")
        if not np.isfinite(features[OFFICIAL_FEATURES].to_numpy(dtype=float)).all():
            raise ValueError("Feature lookup chứa giá trị không hợp lệ")
        if not features.score_year.gt(self.metadata["training_max_year"]).all():
            raise ValueError("Feature phục vụ phải thuộc năm sau dữ liệu huấn luyện")
        self.features = features.set_index(KEYS)
        self.cdf = CDFLookup(pd.read_parquet(self.release / "cdf_summary.parquet"))
        self.metadata["cdf_available_years"] = sorted({year for year, block in self.cdf.groups})

    def predict(self, request):
        start = perf_counter()
        if not isinstance(request, dict):
            raise PredictionError("Request phải là JSON object", 400)
        required = ["score_year", "school_id", "score_code", "score_blocks", "total_score"]
        if any(name not in request for name in required):
            raise PredictionError("Thiếu trường bắt buộc", 400)
        year, score = request["score_year"], request["total_score"]
        if isinstance(year, bool) or not isinstance(year, int) or not 2016 <= year <= 2100:
            raise PredictionError("score_year phải là số nguyên hợp lệ", 400)
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 30:
            raise PredictionError("total_score phải thuộc [0,30] và hữu hạn", 400)
        for name in ("school_id", "score_code", "score_blocks"):
            if not isinstance(request[name], str) or not request[name].strip():
                raise PredictionError(f"{name} phải là chuỗi không rỗng", 400)
        block = request["score_blocks"].strip()
        if block not in BLOCK_NAME_MAP:
            raise PredictionError("Tổ hợp chưa được hỗ trợ")
        key = (request["school_id"].strip(), request["score_code"].strip(), year)
        if key not in self.features.index:
            raise PredictionError("Không có đặc trưng chương trình cho năm yêu cầu", 404)
        row = self.features.loc[key]
        if block not in row.allowed_blocks.split(";"):
            raise PredictionError("Chương trình không sử dụng tổ hợp này")
        try:
            rank = self.cdf.rank(year, block, score)
        except ValueError as error:
            raise PredictionError(str(error)) from error
        vector = pd.DataFrame([row[OFFICIAL_FEATURES].to_numpy(dtype=float)], columns=OFFICIAL_FEATURES)
        mean = float(np.clip(self.models["point_estimator"].predict(vector)[0], 0, 1))
        raw = np.array([self.models[f"quantile_{quantile}"].predict(vector)[0] for quantile in (0.1, 0.5, 0.9)])
        if not np.isfinite(raw).all() or not math.isfinite(mean):
            raise PredictionError("Model trả giá trị không hữu hạn", 503)
        quantiles = np.sort(np.clip(raw, 0, 1))
        sigma = max(float((quantiles[2] - quantiles[0]) / 2.5631031311), 0.001)
        variance = sigma ** 2
        probability = calculate_admission_probability(rank, mean, variance)
        fallbacks = ["previous_year_offering"] if row.offering_carried_forward else []
        return {"status": "success", "model_version": self.release.name,
                "feature_schema_version": FEATURE_SCHEMA_VERSION, "fallbacks_applied": fallbacks,
                "student_percentile": {"block": block, "calculated_rank_pct": rank},
                "admission_percentile_forecast": {"expected_percentile_mean": mean,
                    "expected_percentile_variance": variance,
                    "q10": float(quantiles[0]), "q50": float(quantiles[1]), "q90": float(quantiles[2]),
                    "quantiles_reordered": bool(np.any(np.diff(raw) < 0))},
                "admission_probability": {"probability_value": probability,
                    "probability_percentage": f"{probability * 100:.2f}%",
                    "decision_tier": classify_decision_tier(probability)},
                "uncertainty_method": "normal_approximation_from_q10_q90",
                "inference_latency_ms": (perf_counter() - start) * 1000}
