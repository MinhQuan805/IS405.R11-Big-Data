"""Generate deterministic synthetic data for execution and regression checks."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from admission_core.specs.contracts import BLOCK_NAME_MAP


def generate_demo(root, score_rows=22000, seed=42):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    years = np.arange(2016, 2027)
    rows = max(int(score_rows), len(years) * 10)
    year = np.resize(years, rows)
    scores = {"score_year": year}
    for index, block in enumerate(BLOCK_NAME_MAP.values()):
        scores[block] = np.round(np.clip(rng.normal(19 + 0.3 * index + (year - 2016) * 0.05, 4, rows), 0, 30), 2)
    raw = pd.DataFrame(scores)
    distribution = root / "scores.parquet"
    raw.to_parquet(distribution, index=False)
    majors, cutoff, keywords, annual = [], [], [], []
    for major in range(8):
        majors.append({"score_codes": f"M{major}", "major_name": f"Ngành {major}", "major_group_name": f"Nhóm {major // 2}"})
    for school in range(6):
        school_name = f"Trường {school}"
        keywords.append({"query_id": f"s{school}", "keyword": school_name, "keyword_type": "school"})
        for year_value in years[:-1]:
            annual.append({"query_id": f"s{school}", "year": int(year_value),
                           "interest_mean": 30.0 + school * 5, "interest_season_peak": 50.0 + school * 4})
            for major in range(8):
                cutoff.append({"school_id": f"S{school}", "school_name": school_name,
                    "score_code": f"M{major}", "score_year": int(year_value),
                    "score_admission_name": "Điểm thi THPT", "score_blocks": "A00;A01",
                    "score_mark": float(np.round(16 + 1.25 * school + 0.5 * major +
                        0.05 * (year_value - 2016) + rng.normal(0, 0.15), 2))})
    for group in range(4):
        keywords.append({"query_id": f"g{group}", "keyword": f"Nhóm {group}", "keyword_type": "major_group"})
        for year_value in years[:-1]:
            annual.append({"query_id": f"g{group}", "year": int(year_value),
                           "interest_mean": float(20 + group * 5), "interest_season_peak": float(40 + group * 5)})
    sources = {"score_distribution_ct2006": str(distribution)}
    for name, data in [("cutoff_scores", cutoff), ("majors", majors), ("trend_keywords", keywords), ("trend_annual", annual)]:
        path = root / f"{name}.parquet"
        pd.DataFrame(data).to_parquet(path, index=False)
        sources[name] = str(path)
    for backend in ("local_pandas", "apache_spark"):
        output = root / backend
        config = {"execution_backend": backend, "data_kind": "synthetic", "seed": seed,
            "spark": {"master": "local[2]", "conf": {"spark.sql.shuffle.partitions": "4"}},
            "data_ingestion": {"mode": "direct_data", "direct_sources": sources},
            "data_paths": {"cdf_output": str(output / "cdf.parquet"), "features_output": str(output / "gold.parquet"),
                "models_dir": str(output / "models"), "report_output": str(output / "evaluation.md")},
            "feature_options": {"forecast_year": 2026, "min_training_year": 2018},
            "model_training": {"min_train_years": 2, "hyperparameters": {"n_estimators": 60, "min_child_samples": 5}},
            "quality_gate": {"max_rmse": 0.16, "min_r2": 0.78, "max_bayes_gap_mse": None}}
        (root / f"{backend}.yaml").write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    manifest = {"data_kind": "synthetic", "seed": seed, "score_rows": rows,
                "block_observations": rows * len(BLOCK_NAME_MAP), "cutoff_rows": len(cutoff),
                "years": list(map(int, years)), "purpose": "execution and parity checks"}
    (root / "data_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runs/demo")
    parser.add_argument("--score-rows", type=int, default=22000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(generate_demo(args.output, args.score_rows, args.seed))


if __name__ == "__main__":
    main()
