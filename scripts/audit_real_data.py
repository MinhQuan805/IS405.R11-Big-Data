"""Audit real admission inputs using aggregate counts without exposing candidate IDs."""
import json
from pathlib import Path
import duckdb
import pandas as pd
import pyarrow.parquet as pq
from admission_core.features import parse_blocks


def main():
    connection = duckdb.connect()
    connection.execute("SET threads=2")
    connection.execute("SET memory_limit='1GB'")
    root = Path("data")
    paths = [root / "data-raw/score-distribution" / name for name in
             ("score-distribution-2016-2025-ct2006.parquet", "score-distribution-2025-ct2018.parquet")]
    report = {"score_sources": []}
    for path in paths:
        years = connection.execute('SELECT CAST(Nam AS VARCHAR), count(*) FROM read_parquet(?) GROUP BY Nam ORDER BY Nam', [str(path)]).fetchall()
        identities = connection.execute('''SELECT left(CAST(Nam AS VARCHAR),2), count(*),
            count(DISTINCT SBD), count(*) FILTER (WHERE SBD IS NULL)
            FROM read_parquet(?) GROUP BY 1 ORDER BY 1''', [str(path)]).fetchall()
        report["score_sources"].append({"path": str(path), "years": years,
                                         "year_rows_distinct_ids_missing_ids": identities})
    overlap = connection.execute('''SELECT count(*) FROM
        (SELECT DISTINCT SBD FROM read_parquet(?) WHERE CAST(Nam AS VARCHAR) IN ('25','2025')) a
        JOIN (SELECT DISTINCT SBD FROM read_parquet(?)) b USING (SBD)''', list(map(str, paths))).fetchone()[0]
    report["candidate_id_overlap_2025_between_curricula"] = overlap
    columns = [name for name in pq.ParquetFile(paths[0]).schema_arrow.names if name not in ("Nam", "SBD_New")]
    predicate = " AND ".join(f'a."{name}" IS NOT DISTINCT FROM b."{name}"' for name in columns)
    duplicate_query = f'''WITH a AS (SELECT * FROM read_parquet(?) WHERE Nam='20'),
        b AS (SELECT * FROM read_parquet(?) WHERE Nam='20-2')
        SELECT count(*), count(*) FILTER(WHERE {predicate}) FROM a JOIN b USING(SBD)'''
    shared_ids, identical = connection.execute(duplicate_query, [str(paths[0]), str(paths[0])]).fetchone()
    report["round_2020_duplicate_proof"] = {"shared_ids": shared_ids, "identical_records_except_round_labels": identical}
    cutoff = pd.read_parquet(root / "data-cleaned/admission-cutoff-score/cutoff-scores.parquet")
    thpt = cutoff.loc[cutoff.score_admission_name.eq("Điểm thi THPT") & cutoff.score_year.ge(2016)].copy()
    report["thpt_rows_since_2016"] = len(thpt)
    report["out_of_scale_cutoffs"] = int((~thpt.score_mark.between(0, 30)).sum())
    thpt = thpt.loc[thpt.score_mark.between(0, 30)].copy()
    report["no_supported_blocks"] = int(thpt.score_blocks.map(parse_blocks).map(len).eq(0).sum())
    report["missing_keys"] = thpt[["school_id", "school_name", "score_code", "score_year"]].isna().sum().to_dict()
    majors = pd.read_parquet(root / "data-cleaned/admission-cutoff-score/majors.parquet")
    mapping = majors.assign(score_code=majors.score_codes.str.split(";")).explode("score_code")
    mapping["score_code"] = mapping.score_code.str.strip()
    mapping = mapping.loc[mapping.score_code.notna() & mapping.score_code.ne("")].drop_duplicates(
        ["score_code", "major_name", "major_group_name"])
    ambiguous = mapping.loc[mapping.score_code.duplicated(keep=False)]
    report["ambiguous_major_code_count"] = int(ambiguous.score_code.nunique())
    report["ambiguous_mapping_rows"] = len(ambiguous)
    report["ambiguous_major_examples"] = ambiguous[["score_code", "major_id", "major_name", "major_group_name"]].head(12).to_dict("records")
    report["unmapped_cutoff_rows"] = int((~thpt.score_code.isin(mapping.score_code)).sum())
    report["unmapped_codes_sample"] = thpt.loc[~thpt.score_code.isin(mapping.score_code), "score_code"].value_counts().head(15).to_dict()
    summary = {key: value for key, value in report.items() if key != "ambiguous_major_examples"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    Path("reports/real_data_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
