"""Command-line entry points for batch stages and model serving."""
import argparse
import json
import yaml
from admission_core.pipeline import AdmissionPipeline


def load_yaml_config(config_path):
    with open(config_path, encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def main():
    parser = argparse.ArgumentParser(description="Admission data pipeline")
    commands = parser.add_subparsers(dest="command")
    run = commands.add_parser("run")
    run.add_argument("--config", default="config/pipeline_config.yaml")
    stage = commands.add_parser("run-stage")
    stage.add_argument("--config", default="config/pipeline_config.yaml")
    stage.add_argument("--stage", choices=["ingest", "cdf", "features", "train"], required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--models-dir", default="models")
    args = parser.parse_args()
    if args.command is None:
        args.command = "run"
        args.config = "config/pipeline_config.yaml"
    if args.command == "serve":
        from admission_core.http_api import start_server
        start_server(args.host, args.port, args.models_dir)
        return
    pipeline = AdmissionPipeline(load_yaml_config(args.config))
    result = pipeline.execute() if args.command == "run" else pipeline.run_stage(args.stage)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
