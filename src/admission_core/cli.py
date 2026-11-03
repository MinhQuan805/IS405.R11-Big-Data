"""Unified Command Line Interface (CLI) for Admission Core Framework.
Supports running the full pipeline, dry-running stages, serving, and reporting.
"""

import argparse
import sys
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from admission_core.pipeline import AdmissionPipeline

def load_yaml_config(config_path: str):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="Admission Core Framework CLI")
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực thi")

    # 1. Lệnh run: Chạy toàn bộ pipeline
    run_parser = subparsers.add_parser("run", help="Chạy toàn bộ pipeline từ đầu đến cuối")
    run_parser.add_argument("--config", default="config/pipeline_config.yaml", help="Đường dẫn file cấu hình")

    # 2. Lệnh run-stage: Chạy riêng 1 công đoạn
    stage_parser = subparsers.add_parser("run-stage", help="Chạy riêng một công đoạn để kiểm thử")
    stage_parser.add_argument("--stage", required=True, choices=["ingest", "cdf", "features", "train"], help="Tên công đoạn")
    stage_parser.add_argument("--config", default="config/pipeline_config.yaml", help="Đường dẫn file cấu hình")

    # 3. Lệnh serve: Khởi chạy Serving Endpoint
    serve_parser = subparsers.add_parser("serve", help="Khởi chạy Model Serving API Server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host lắng nghe")
    serve_parser.add_argument("--port", type=int, default=8000, help="Cổng lắng nghe")

    args = parser.parse_args()

    if args.command == "run" or args.command is None:
        cfg_path = getattr(args, "config", "config/pipeline_config.yaml")
        cfg = load_yaml_config(cfg_path)
        pipeline = AdmissionPipeline(cfg)
        pipeline.execute()

    elif args.command == "run-stage":
        cfg = load_yaml_config(args.config)
        pipeline = AdmissionPipeline(cfg)
        if args.stage == "cdf":
            sources = pipeline.ingestion_backend.ingest(cfg)
            cdf_out = cfg.get("data_paths", {}).get("cdf_output", "data-cleaned/score-distribution-cdf/cdf_summary.parquet")
            out = pipeline.cdf_backend.compute_cdf(sources, cdf_out)
            print(f"[Run-Stage] Hoàn tất CDF Stage: {out}")
        elif args.stage == "features":
            sources = pipeline.ingestion_backend.ingest(cfg)
            feat_inputs = {
                "cutoff_scores": sources.get("cutoff_scores"),
                "majors": sources.get("majors"),
                "trend_annual": sources.get("trend_annual"),
                "trend_keywords": sources.get("trend_keywords"),
                "cdf_data": cfg.get("data_paths", {}).get("cdf_output", "data-cleaned/score-distribution-cdf/cdf_summary.parquet")
            }
            feat_out = cfg.get("data_paths", {}).get("features_output", "data-cleaned/gold_features.parquet")
            out = pipeline.feature_backend.build_features(feat_inputs, feat_out)
            print(f"[Run-Stage] Hoàn tất Features Stage: {out}")
        else:
            print(f"[Run-Stage] Công đoạn '{args.stage}' đang được thực hiện.")

    elif args.command == "serve":
        from serving.app import start_server
        start_server(host=args.host, port=args.port)

if __name__ == "__main__":
    main()

