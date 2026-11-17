"""Standalone long-format CDF job with no framework imports."""
import argparse
from pathlib import Path
import pandas as pd

BLOCKS = {"A00": "KhoiA", "A01": "KhoiA1", "B00": "KhoiB", "C00": "KhoiC",
          "D01": "KhoiD", "A02": "KhoiA02", "C01": "KhoiC01", "D07": "KhoiD07"}


def normalize(frame, ct2018=False):
    keys = ["score_year", "block_name", "score_value"]
    if not set(keys).issubset(frame.columns):
        frame = frame.copy()
        if "score_year" not in frame:
            if "Nam" in frame:
                mapping = {str(year)[2:]: year for year in range(2016, 2100)}
                mapping.update({"20-2": 2020, "21-2": 2021})
                frame["score_year"] = frame.Nam.astype(str).replace(mapping)
            elif ct2018:
                frame["score_year"] = 2025
            else:
                raise ValueError("Phổ điểm thiếu năm")
        columns = [block for block in BLOCKS.values() if block in frame]
        if not columns:
            raise ValueError("Phổ điểm thiếu tổ hợp")
        frame = frame.melt(id_vars="score_year", value_vars=columns,
                           var_name="block_name", value_name="score_value")
    frame = frame[keys].copy()
    frame["score_year"] = pd.to_numeric(frame.score_year, errors="coerce")
    frame["score_value"] = pd.to_numeric(frame.score_value, errors="coerce")
    frame["block_name"] = frame.block_name.replace(BLOCKS)
    return frame.loc[frame.score_value.between(0, 30) & frame.score_year.between(2016, 2100) &
                     frame.score_year.mod(1).eq(0) & frame.block_name.isin(BLOCKS.values())]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--input-ct2018")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    frames = [normalize(pd.read_parquet(args.input))]
    if args.input_ct2018:
        frames.append(normalize(pd.read_parquet(args.input_ct2018), ct2018=True))
    observations = pd.concat(frames, ignore_index=True)
    keys = ["score_year", "block_name", "score_value"]
    if not set(keys).issubset(observations.columns):
        raise ValueError("Script độc lập nhận dữ liệu điểm dạng dài theo score_year, block_name, score_value")
    observations = observations.loc[observations.score_value.between(0, 30) & observations.score_year.between(2016, 2100)].dropna(subset=keys)
    counts = observations.groupby(keys, as_index=False).size().rename(columns={"size": "candidate_count"}).sort_values(keys)
    if counts.empty:
        raise ValueError("Không có điểm hợp lệ")
    groups = counts.groupby(keys[:2])
    counts["total_candidates"] = groups.candidate_count.transform("sum")
    counts["cdf_leq"] = groups.candidate_count.cumsum() / counts.total_candidates
    counts["rank_pct_gt"] = 1 - counts.cdf_leq
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    counts.to_parquet(args.output, index=False)


if __name__ == "__main__":
    main()
