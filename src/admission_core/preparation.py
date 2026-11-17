"""Prepare admission identities with auditable, title-based major resolution."""
import json
from pathlib import Path
import re
import unicodedata
import pandas as pd
from admission_core.features import KEYS, parse_blocks


def normalize_title(value):
    text = unicodedata.normalize("NFKD", str(value).lower().replace("đ", "d"))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def resolve_major(title, candidates):
    """Resolve only a unique alias or a unique longest catalog phrase."""
    candidates = sorted(set(candidates))
    if len(candidates) == 1:
        return (*candidates[0], "unique_code")
    main = normalize_title(re.sub(r"\([^)]*\)", " ", str(title)))
    full = normalize_title(title)
    for text in dict.fromkeys([main, full]):
        exact = [candidate for candidate in candidates if normalize_title(candidate[0]) == text]
        if len(exact) == 1:
            return (*exact[0], "exact_title")
        matches = [candidate for candidate in candidates
                   if f" {normalize_title(candidate[0])} " in f" {text} "]
        if matches:
            longest = max(len(normalize_title(candidate[0]).split()) for candidate in matches)
            best = [candidate for candidate in matches if len(normalize_title(candidate[0]).split()) == longest]
            if len(best) == 1:
                return (*best[0], "unique_longest_title")
    return None, None, "unresolved"


def prepare_real_inputs(data_root="data", output_root=None):
    data_root = Path(data_root)
    output_root = Path(output_root or data_root / "data-cleaned/v3/prepared")
    output_root.mkdir(parents=True, exist_ok=True)
    cutoff = pd.read_parquet(data_root / "data-cleaned/admission-cutoff-score/cutoff-scores.parquet")
    majors = pd.read_parquet(data_root / "data-cleaned/admission-cutoff-score/majors.parquet")
    report = {"input_rows": len(cutoff), "exclusions": {}}
    cutoff["exclusion_reason"] = ""
    policies = [
        ("other_admission_method", cutoff.score_admission_name.ne("Điểm thi THPT")),
        ("before_2016", cutoff.score_year.lt(2016)),
        ("non_university", cutoff.school_type.ne("Đại học")),
        ("cutoff_outside_30_scale", ~cutoff.score_mark.between(0, 30)),
        ("no_supported_block", cutoff.score_blocks.map(parse_blocks).map(len).eq(0)),
    ]
    for reason, condition in policies:
        selected = cutoff.exclusion_reason.eq("") & condition
        report["exclusions"][reason] = int(selected.sum())
        cutoff.loc[selected, "exclusion_reason"] = reason
    excluded = cutoff.loc[cutoff.exclusion_reason.ne("")].copy()
    eligible = cutoff.loc[cutoff.exclusion_reason.eq("")].drop(columns="exclusion_reason").copy()
    for name in ("school_id", "score_code"):
        eligible[name] = eligible[name].astype(str).str.strip()
    exploded = majors.assign(score_code=majors.score_codes.str.split(";")).explode("score_code")
    exploded["score_code"] = exploded.score_code.str.strip()
    choices = {code: list(zip(group.major_name, group.major_group_name))
               for code, group in exploded.groupby("score_code")}
    cache = {}
    resolved = []
    for row in eligible.itertuples():
        key = (row.score_code, row.score_name)
        if key not in cache:
            cache[key] = resolve_major(row.score_name, choices.get(row.score_code, []))
        resolved.append(cache[key])
    eligible[["resolved_major", "resolved_group", "mapping_method"]] = resolved
    identified = eligible.loc[eligible.resolved_major.notna(), KEYS + ["resolved_major", "resolved_group"]].drop_duplicates()
    conflicts = identified.loc[identified.duplicated(KEYS, keep=False), KEYS].drop_duplicates()
    report["conflicting_program_year_keys"] = len(conflicts)
    identified = identified.merge(conflicts.assign(conflict=True), on=KEYS, how="left")
    identified = identified.loc[identified.conflict.isna()].drop(columns="conflict")
    eligible = eligible.drop(columns=["resolved_major", "resolved_group"]).merge(identified, on=KEYS, how="left", validate="many_to_one")
    unresolved = eligible.resolved_major.isna()
    report["exclusions"]["unresolved_or_conflicting_major"] = int(unresolved.sum())
    rejected = eligible.loc[unresolved].copy()
    rejected["exclusion_reason"] = "unresolved_or_conflicting_major"
    excluded = pd.concat([excluded, rejected], ignore_index=True)
    retained = eligible.loc[~unresolved].copy()
    retained.loc[retained.mapping_method.eq("unresolved"), "mapping_method"] = "same_program_year"
    mapping = retained[KEYS + ["resolved_major", "resolved_group"]].drop_duplicates().rename(
        columns={"score_code": "score_codes", "resolved_major": "major_name", "resolved_group": "major_group_name"})
    report["retained_rows"] = len(retained)
    report["retained_program_years"] = len(mapping)
    report["retained_by_year"] = {str(key): int(value) for key, value in retained.score_year.value_counts().sort_index().items()}
    report["mapping_methods"] = retained.mapping_method.value_counts().to_dict()
    report["policy"] = "university THPT, score in [0,30], supported block, unique catalog phrase within school/program/year"
    if retained.empty:
        raise ValueError("Không có điểm chuẩn hợp lệ sau chuẩn bị dữ liệu")
    retained.to_parquet(output_root / "cutoff-scores.parquet", index=False)
    mapping.to_parquet(output_root / "majors.parquet", index=False)
    retained[KEYS + ["score_name", "resolved_major", "resolved_group", "mapping_method"]].to_csv(
        output_root / "mapping_review.csv", index=False, encoding="utf-8-sig")
    excluded.to_parquet(output_root / "excluded-cutoffs.parquet", index=False)
    (output_root / "preparation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
