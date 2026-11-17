"""Exercise HTTP inference using a published synthetic-data model release."""
import argparse
import json
from pathlib import Path
from threading import Thread
from time import perf_counter
from urllib.request import Request, urlopen
import numpy as np
from admission_core.http_api import create_server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-dir", required=True)
    parser.add_argument("--output", default="reports/serving_verification.json")
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()
    if args.requests < 1:
        parser.error("requests phải dương")
    server = create_server(port=0, models_dir=args.models_dir)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/api/v2"
    samples, results = [], []
    try:
        with urlopen(base + "/health", timeout=10) as response:
            assert json.load(response)["status"] == "ready"
        for index in range(args.requests + 5):
            body = {"score_year": 2026, "school_id": "S0" if index % 2 == 0 else "S5",
                    "score_code": "M0", "score_blocks": "A00", "total_score": 23.0}
            request = Request(base + "/predict/admission-probability", json.dumps(body).encode(),
                              {"Content-Type": "application/json"})
            start = perf_counter()
            with urlopen(request, timeout=10) as response:
                result = json.load(response)
            elapsed = (perf_counter() - start) * 1000
            assert result["status"] == "success"
            if index >= 5:
                samples.append(elapsed)
                results.append(result)
        output = {"workload": "synthetic programs S0/M0 and S5/M0, score 23, year 2026",
                  "concurrency": 1, "requests": args.requests, "warmup_requests": 5,
                  "latency_p50_ms": float(np.percentile(samples, 50)),
                  "latency_p95_ms": float(np.percentile(samples, 95)),
                  "samples_ms": samples, "example_predictions": results[:2]}
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({key: value for key, value in output.items() if key not in {"samples_ms", "example_predictions"}}, indent=2))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
