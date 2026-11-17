"""Execute batch stages and publish only complete, accepted model releases."""
import json
import time
from pathlib import Path
from uuid import uuid4
import pandas as pd
from admission_core.factory import get_ingestion_backend, get_cdf_backend, get_feature_backend, get_trainer_backend, validate_backend
from admission_core.validation.quality_gate import QualityGate
from admission_core.reporting.reporter import ReportGenerator
from admission_core.artifacts import publish
from admission_core.backends.apache_spark.session import SparkRuntime


class AdmissionPipeline:
    def __init__(self, config):
        self.config = dict(config)
        validate_backend(config)
        self.runtime = SparkRuntime(config.get("spark"))
        self.ingestion_backend = get_ingestion_backend(config)
        self.cdf_backend = get_cdf_backend(config, self.runtime)
        self.feature_backend = get_feature_backend(config, self.runtime)
        self.trainer_backend = get_trainer_backend(config)
        self.quality_gate = QualityGate(config.get("quality_gate"))
        self.paths = dict(config.get("data_paths", {}))
        self.config["data_paths"] = self.paths

    def ingest(self):
        policy = self.config.get("reliability", {}).get("retry_policy", {})
        attempts = int(policy.get("max_attempts", 1))
        if attempts < 1:
            raise ValueError("max_attempts phải dương")
        for index in range(attempts):
            try:
                return self.ingestion_backend.ingest(self.config)
            except (OSError, RuntimeError):
                if index == attempts - 1:
                    raise
                time.sleep(min(30, policy.get("initial_backoff_sec", 1) * policy.get("backoff_multiplier", 2) ** index))

    def feature_inputs(self, sources, cdf_path):
        return {**sources, "cdf_data": cdf_path}

    def train(self, features, cdf):
        root = Path(self.paths.get("models_dir", "models"))
        candidate = root / "versions" / uuid4().hex
        candidate.mkdir(parents=True, exist_ok=False)
        training_options = dict(self.config.get("model_training", {}))
        training_options["data_kind"] = self.config.get("data_kind", "unspecified")
        metrics = self.trainer_backend.train_and_evaluate(features, str(candidate), training_options)
        passed, message = self.quality_gate.validate(metrics)
        metrics["quality_gate_passed"] = passed
        metrics["quality_gate_message"] = message
        (candidate / "evaluation.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        ReportGenerator.generate_markdown(metrics, str(candidate / "evaluation.md"))
        if not passed:
            raise RuntimeError(f"Model ứng viên không đạt. Bản hiện hành được giữ nguyên. {message}")
        from admission_core.cdf_contract import validate_cdf
        cdf_frame = validate_cdf(pd.read_parquet(cdf))
        cdf_frame.to_parquet(candidate / "cdf_summary.parquet", index=False)
        (candidate / "run_config.json").write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8")
        # Load the entire candidate before promotion, including models and lookups.
        from admission_core.inference import AdmissionPredictor
        AdmissionPredictor(candidate)
        ReportGenerator.generate_markdown(metrics, self.paths.get("report_output", "reports/evaluation_summary.md"))
        publish(candidate, root)
        return metrics

    def run_stage(self, stage):
        try:
            if stage == "train":
                return self.train(self.paths["features_output"], self.paths["cdf_output"])
            sources = self.ingest()
            if stage == "ingest":
                return sources
            if stage == "cdf":
                return self.cdf_backend.compute_cdf(sources, self.paths["cdf_output"], self.config.get("cdf_options"))
            if stage == "features":
                return self.feature_backend.build_features(self.feature_inputs(sources, self.paths["cdf_output"]),
                    self.paths["features_output"], self.config.get("feature_options"))
            raise ValueError(f"Stage không hợp lệ: {stage}")
        finally:
            self.runtime.close()

    def execute(self):
        try:
            run_id = uuid4().hex
            for key in ("cdf_output", "features_output"):
                uri = self.paths[key]
                if "://" in uri:
                    parent, _, name = uri.rpartition("/")
                    self.paths[key] = f"{parent}/runs/{run_id}/{name}"
                else:
                    destination = Path(uri)
                    self.paths[key] = str(destination.parent / "runs" / run_id / destination.name)
            sources = self.ingest()
            cdf = self.cdf_backend.compute_cdf(sources, self.paths["cdf_output"], self.config.get("cdf_options"))
            features = self.feature_backend.build_features(self.feature_inputs(sources, cdf),
                self.paths["features_output"], self.config.get("feature_options"))
            return self.train(features, cdf)
        finally:
            self.runtime.close()
