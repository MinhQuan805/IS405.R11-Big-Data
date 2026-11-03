"""Admission Pipeline Orchestrator (The 'Túi Mù' / Black Box Engine).
Executes the end-to-end lifecycle with automated Retry, Fallback, and Rollback.
"""

import time
import shutil
from pathlib import Path
from typing import Dict, Any

from admission_core.factory import (
    get_ingestion_backend, get_cdf_backend, get_feature_backend, get_trainer_backend
)
from admission_core.validation.quality_gate import QualityGate
from admission_core.reporting.reporter import ReportGenerator

class AdmissionPipeline:
    """Khung điều phối quy trình tự động hóa độc lập công nghệ"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ingestion_backend = get_ingestion_backend(config)
        self.cdf_backend = get_cdf_backend(config)
        self.feature_backend = get_feature_backend(config)
        self.trainer_backend = get_trainer_backend(config)
        self.quality_gate = QualityGate(config.get("quality_gate"))

    def execute(self) -> Dict[str, Any]:
        print("=" * 70)
        print("🚀 BẮT ĐẦU VẬN HÀNH PIPELINE TỰ ĐỘNG HÓA ('TÚI MÙ' FRAMEWORK)")
        print("=" * 70)

        # 1. BƯỚC 1: INGESTION (Nạp dữ liệu với cơ chế Retry)
        max_retries = self.config.get("reliability", {}).get("retry_policy", {}).get("max_attempts", 3)
        sources = None
        for attempt in range(1, max_retries + 1):
            try:
                sources = self.ingestion_backend.ingest(self.config)
                break
            except Exception as e:
                print(f"⚠️ [Retry {attempt}/{max_retries}] Lỗi Ingestion: {e}")
                if attempt == max_retries:
                    raise
                time.sleep(2 ** attempt)

        # 2. BƯỚC 2: CDF ENGINE (Module 2)
        cdf_out = self.config.get("data_paths", {}).get("cdf_output", "data-cleaned/score-distribution-cdf/cdf_summary.parquet")
        cdf_path = self.cdf_backend.compute_cdf(sources, cdf_out)

        # 3. BƯỚC 3: FEATURE PIPELINE (Module 1 & 3)
        feature_inputs = {
            "cutoff_scores": sources.get("cutoff_scores"),
            "majors": sources.get("majors"),
            "trend_annual": sources.get("trend_annual"),
            "trend_keywords": sources.get("trend_keywords"),
            "cdf_data": cdf_path
        }
        feat_out = self.config.get("data_paths", {}).get("features_output", "data-cleaned/gold_features.parquet")
        feat_path = self.feature_backend.build_features(feature_inputs, feat_out)

        # 4. BƯỚC 4: TRAINER (Module 3)
        model_out = self.config.get("data_paths", {}).get("models_dir", "models/")
        
        # Sao lưu phiên bản trước phục vụ cơ chế Rollback nếu cần
        backup_model_dir = Path("models_backup/")
        if Path(model_out).exists():
            shutil.copytree(model_out, backup_model_dir, dirs_exist_ok=True)

        metrics = self.trainer_backend.train_and_evaluate(
            feature_matrix_uri=feat_path,
            output_model_dir=model_out,
            options=self.config.get("model_training")
        )

        # 5. BƯỚC 5: QUALITY GATE & ROLLBACK
        passed, gate_msg = self.quality_gate.validate(metrics)
        print(f"[Quality Gate] {gate_msg}")

        if not passed:
            print("🚨 KÍCH HOẠT CƠ CHẾ ROLLBACK: Mô hình mới không vượt qua cổng kiểm định!")
            if backup_model_dir.exists():
                shutil.copytree(backup_model_dir, model_out, dirs_exist_ok=True)
                print("🔄 Đã khôi phục thành công phiên bản mô hình trước đó.")
            raise RuntimeError(f"Pipeline dừng do vi phạm Quality Gate: {gate_msg}")

        # 6. BƯỚC 6: XUẤT BÁO CÁO TỰ ĐỘNG
        report_path = self.config.get("data_paths", {}).get("report_output", "reports/evaluation_summary.md")
        ReportGenerator.generate_markdown(metrics, report_path)

        print("=" * 70)
        print("✅ HOÀN TẤT TOÀN BỘ PIPELINE THÀNH CÔNG RỰC RỠ!")
        print("=" * 70)
        return metrics

