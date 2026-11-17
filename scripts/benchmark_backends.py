"""Measure isolated backend runs, including Python, JVM and worker RSS."""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from uuid import uuid4
import pandas as pd
import psutil
import yaml
from admission_core.pipeline import AdmissionPipeline
from admission_core.cdf_contract import CDF_KEYS
from admission_core.features import KEYS


def worker(config_path, backend, output):
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    config["execution_backend"] = backend
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    pipeline = AdmissionPipeline(config)
    start = time.perf_counter()
    try:
        sources = pipeline.ingest()
        before_session = time.perf_counter()
        if backend == "apache_spark":
            pipeline.runtime.session.range(1).count()
        initialized = time.perf_counter()
        cdf = pipeline.cdf_backend.compute_cdf(sources, str(output / "cdf.parquet"), config.get("cdf_options"))
        after_cdf = time.perf_counter()
        pipeline.feature_backend.build_features({**sources, "cdf_data": cdf}, str(output / "gold.parquet"), config.get("feature_options"))
        after_features = time.perf_counter()
        metrics = {"backend": backend, "initialization_seconds": initialized - before_session,
            "cdf_seconds": after_cdf - initialized, "features_seconds": after_features - after_cdf,
            "processing_total_seconds": after_features - start, "spark": config.get("spark"),
            "data_kind": config.get("data_kind", "unspecified")}
        (output / "timing.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    finally:
        pipeline.runtime.close()


def measure(config, backend, output):
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--config", str(config),
               "--backend", backend, "--output", str(output)]
    peak = 0
    started = time.perf_counter()
    with Path(str(output) + ".log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        parent = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                members = [parent] + parent.children(recursive=True)
                rss = 0
                for member in members:
                    try:
                        rss += member.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                        pass
                peak = max(peak, rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                pass
            time.sleep(0.05)
    if process.returncode:
        raise RuntimeError(f"Benchmark thất bại. Xem {output}.log")
    metrics = json.loads((output / "timing.json").read_text(encoding="utf-8"))
    metrics.update(peak_tree_rss_mb=peak / 1024 ** 2, wall_seconds=time.perf_counter() - started)
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="runs/benchmark")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--backend", choices=["local_pandas", "apache_spark"])
    args = parser.parse_args()
    if args.worker:
        worker(args.config, args.backend, args.output)
        return
    if args.repeats < 1:
        parser.error("repeats phải dương")
    root = Path(args.output).resolve() / uuid4().hex
    root.mkdir(parents=True)
    measurements = []
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    for repeat in range(args.repeats):
        outputs = {}
        for backend in ("local_pandas", "apache_spark"):
            output = root / f"{backend}-{repeat}"
            metrics = measure(args.config, backend, output)
            metrics["repeat"] = repeat
            measurements.append(metrics)
            outputs[backend] = output
        for filename, keys in [("cdf.parquet", CDF_KEYS), ("gold.parquet", KEYS)]:
            left = pd.read_parquet(outputs["local_pandas"] / filename).sort_values(keys).reset_index(drop=True).sort_index(axis=1)
            right = pd.read_parquet(outputs["apache_spark"] / filename).sort_values(keys).reset_index(drop=True).sort_index(axis=1)
            pd.testing.assert_frame_equal(left, right, check_dtype=False, atol=1e-8, rtol=1e-8)
        print(f"Repeat {repeat + 1}: parity passed", flush=True)
    result = {"environment": {"platform": platform.platform(), "python": sys.version,
              "cpu_count": os.cpu_count(), "ram_gb": psutil.virtual_memory().total / 1024 ** 3,
              "windows_local_fs_jar": os.environ.get("ADMISSION_WINDOWS_FS_JAR"),
              "java_version": subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.strip()},
              "config": config, "measurements": measurements, "output_parity": True,
              "memory_method": "50ms samples, sum RSS of live process tree; shared pages may be counted more than once"}
    (root / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(measurements).to_csv(root / "measurements.csv", index=False)
    lines = ["# Kết quả so sánh backend", "", f"Nguồn dữ liệu {config.get('data_kind', 'unspecified')}.", "",
             "Mỗi lần đo khởi tạo tiến trình mới. Thời gian khởi tạo và xử lý được ghi riêng.", "",
             "| Backend | Số lần | CDF trung vị (s) | Features trung vị (s) | Peak RSS trung vị (MiB) |",
             "| --- | --- | --- | --- | --- |"]
    for backend in ("local_pandas", "apache_spark"):
        selected = [row for row in measurements if row["backend"] == backend]
        medians = [statistics.median(row[key] for row in selected) for key in ("cdf_seconds", "features_seconds", "peak_tree_rss_mb")]
        lines.append(f"| {backend} | {len(selected)} | {medians[0]:.4f} | {medians[1]:.4f} | {medians[2]:.1f} |")
    lines.extend(["", "Kiểm tra tương đương CDF và Gold đạt ở mọi lần đo.",
                  "", "RSS cộng theo cây tiến trình có thể đếm lặp trang bộ nhớ dùng chung. Kết quả phụ thuộc chu kỳ lấy mẫu.", ""])
    (root / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(root)


if __name__ == "__main__":
    main()
