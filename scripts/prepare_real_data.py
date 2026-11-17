"""Prepare supplied real admission datasets without modifying source files."""
import argparse
import json
from admission_core.preparation import prepare_real_inputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--output")
    args = parser.parse_args()
    print(json.dumps(prepare_real_inputs(args.data_root, args.output), ensure_ascii=False, indent=2))
