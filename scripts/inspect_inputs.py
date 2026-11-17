"""Inventory configured input datasets without executing the pipeline."""
import argparse
import json
from pathlib import Path
import pyarrow.dataset as ds
import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/pipeline_config.yaml")
    parser.add_argument("--output", default="reports/input_inventory.json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    inventory = []
    for name, uri in config.get("data_ingestion", {}).get("direct_sources", {}).items():
        item = {"source": name, "uri": uri}
        if not uri:
            item["state"] = "not_configured"
        elif "://" in uri:
            item["state"] = "remote_not_checked"
        else:
            path = Path(uri)
            if not path.exists():
                item["state"] = "missing"
            else:
                try:
                    dataset = ds.dataset(path, format="parquet")
                    files = [path] if path.is_file() else list(path.rglob("*.parquet"))
                    item.update(state="available", rows=dataset.count_rows(),
                                bytes=sum(file.stat().st_size for file in files),
                                schema=str(dataset.schema))
                except (OSError, ValueError) as error:
                    item.update(state="invalid", error=str(error))
        inventory.append(item)
    report = {"config": str(Path(args.config).resolve()), "data_kind": config.get("data_kind", "unspecified"),
              "inputs": inventory}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({item["source"]: item["state"] for item in inventory}, ensure_ascii=False, indent=2))
    if args.strict and any(item["state"] != "available" for item in inventory):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
