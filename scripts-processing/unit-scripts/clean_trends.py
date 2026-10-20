# Auto-generated script from clean-trends.ipynb
# export
import json
from pathlib import Path
import sys
import pandas as pd

# Thêm thư mục gốc vào sys.path để nạp helper
PROJECT_ROOT = Path('.').resolve().parents[1] if Path('.').resolve().name == 'notebooks' else Path('.').resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Cấu hình UTF-8 an toàn trên Windows
if sys.platform == 'win32':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8')
            except Exception:
                pass

from helpers.get_configs import get_config

# Cấu hình đường dẫn dữ liệu thô (Raw Data)
RAW_TOPICS_PATH = get_config('dirs.yaml', ['raw_data', 'trend_topics'], as_path=True)
RAW_TRENDS_PATH = get_config('dirs.yaml', ['raw_data', 'trends'], as_path=True)

# Cấu hình đường dẫn dữ liệu làm sạch (Cleaned Data)
CLEANED_TOPICS_PATH = get_config('dirs.yaml', ['cleaned_data', 'trend_topics'], as_path=True)
CLEANED_QUERIES_PATH = get_config('dirs.yaml', ['cleaned_data', 'trend_queries'], as_path=True)
CLEANED_KEYWORDS_PATH = get_config('dirs.yaml', ['cleaned_data', 'trend_keywords'], as_path=True)
CLEANED_TIMELINE_PATH = get_config('dirs.yaml', ['cleaned_data', 'trend_timeline'], as_path=True)
CLEANED_ANNUAL_PATH = get_config('dirs.yaml', ['cleaned_data', 'trend_annual'], as_path=True)
CLEANED_REGIONS_PATH = get_config('dirs.yaml', ['cleaned_data', 'trend_regions'], as_path=True)
CLEANED_RELATED_PATH = get_config('dirs.yaml', ['cleaned_data', 'trend_related_queries'], as_path=True)

# Cấu hình đường dẫn script đầu ra
SCRIPT_OUTPUT_PATH = get_config('dirs.yaml', ['unit_scripts', 'clean_trends'], as_path=True)


def clean_str(val):
    """Chuẩn hóa chuỗi văn bản: xóa khoảng trắng thừa, xử lý giá trị rỗng."""
    if val is None or pd.isna(val):
        return ""
    return " ".join(str(val).split())

# ======================================================================

# export
def clean_trend_topics():
    """Làm sạch, chuẩn hóa ký tự trắng và loại bỏ bản ghi trùng lặp trong trend_topics.parquet."""
    print("--- 1. Làm sạch trend_topics.parquet ---")
    df_raw = pd.read_parquet(RAW_TOPICS_PATH)
    for col in df_raw.columns:
        df_raw[col] = df_raw[col].apply(clean_str)

    df_raw = df_raw[df_raw["keyword"] != ""].copy()
    df_clean = df_raw.drop_duplicates(subset=["keyword", "keyword_type", "mid", "title"]).reset_index(drop=True)

    CLEANED_TOPICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(CLEANED_TOPICS_PATH, index=False)
    print(f"Đã lưu cleaned trend_topics.parquet: {len(df_clean):,} dòng (từ {len(df_raw):,} dòng thô).")
    return df_clean

# ======================================================================

# export
def clean_trends_json():
    """Tách và chuẩn hóa trends.json thành các bảng quan hệ Parquet chuyên biệt."""
    print("--- 2. Tách và chuẩn hóa trends.json ---")
    with open(RAW_TRENDS_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    queries_list = []
    keywords_list = []
    timeline_list = []
    annual_list = []
    regions_list = []
    related_list = []

    for r in records:
        qid = r.get("query_id")
        q = r.get("query", "")
        q_kind = r.get("query_kind", "")
        mid = r.get("mid", "") or ""
        title = r.get("title", "") or ""
        topic_type = r.get("type", "") or ""
        score = r.get("selection_score", 0.0)
        status = r.get("status", "")
        geo = r.get("geo", "")
        date_range = r.get("date_range", "")

        stage_status = r.get("stage_status", {})
        st_interest = stage_status.get("interest", "")
        st_enrichment = stage_status.get("enrichment", "")
        enrichment_skip_reason = stage_status.get("enrichment_skip_reason", "") or ""

        iot = r.get("interest_over_time") or {}
        nonzero_points = iot.get("nonzero_points", 0)
        avg_interest = iot.get("average_interest", 0.0)
        max_interest = iot.get("max_interest", 0)

        # 1. Bảng trend_queries
        queries_list.append({
            "query_id": qid,
            "query": q,
            "query_kind": q_kind,
            "mid": mid,
            "title": title,
            "type": topic_type,
            "selection_score": score,
            "status": status,
            "stage_interest": st_interest,
            "stage_enrichment": st_enrichment,
            "enrichment_skip_reason": enrichment_skip_reason,
            "nonzero_points": nonzero_points,
            "average_interest": avg_interest,
            "max_interest": max_interest,
            "geo": geo,
            "date_range": date_range,
        })

        # 2. Bảng trend_keywords (Ánh xạ 1-N thực thể tuyển sinh sang query_id)
        kw_meta = r.get("keyword_metadata", [])
        if kw_meta:
            for km in kw_meta:
                keywords_list.append({
                    "query_id": qid,
                    "keyword": clean_str(km.get("keyword")),
                    "keyword_type": clean_str(km.get("keyword_type")),
                    "selected_mid": clean_str(km.get("selected_mid")),
                    "selected_title": clean_str(km.get("selected_title")),
                    "relevance_score": km.get("relevance_score", 0.0),
                    "selection_reason": km.get("selection_reason", ""),
                    "candidate_count": km.get("candidate_count", 1),
                })
        else:
            kws = r.get("keywords", [])
            types = r.get("keyword_types", [])
            for kw, kt in zip(kws, types):
                keywords_list.append({
                    "query_id": qid,
                    "keyword": clean_str(kw),
                    "keyword_type": clean_str(kt),
                    "selected_mid": mid,
                    "selected_title": title,
                    "relevance_score": score,
                    "selection_reason": "default",
                    "candidate_count": 1,
                })

        # 3. Bảng trend_timeline & 4. trend_annual
        timeline = iot.get("timeline", [])
        yearly_buckets = {}
        for pt in timeline:
            raw_date = pt.get("date", "")
            val = pt.get("value", 0)
            date_clean = raw_date[:10]
            year = int(date_clean[:4])
            month = int(date_clean[5:7])

            timeline_list.append({
                "query_id": qid,
                "date": date_clean,
                "year": year,
                "month": month,
                "interest": val,
            })

            if year not in yearly_buckets:
                yearly_buckets[year] = {"values": [], "season_values": [], "nonzero": 0}
            yearly_buckets[year]["values"].append(val)
            if val > 0:
                yearly_buckets[year]["nonzero"] += 1
            if month in (5, 6, 7, 8):  # Mùa cao điểm tuyển sinh
                yearly_buckets[year]["season_values"].append(val)

        for year, bucket in yearly_buckets.items():
            vals = bucket["values"]
            s_vals = bucket["season_values"]
            annual_list.append({
                "query_id": qid,
                "year": year,
                "interest_mean": round(sum(vals) / len(vals), 4) if vals else 0.0,
                "interest_max": max(vals) if vals else 0,
                "interest_sum": sum(vals),
                "interest_season_peak": round(sum(s_vals) / len(s_vals), 4) if s_vals else 0.0,
                "nonzero_months": bucket["nonzero"],
            })

        # 5. Bảng trend_regions (Quan tâm theo tỉnh thành)
        ibr = r.get("interest_by_region")
        if ibr and "regions" in ibr and isinstance(ibr["regions"], list):
            for item in ibr["regions"]:
                regions_list.append({
                    "query_id": qid,
                    "region": clean_str(item.get("region")),
                    "rank": item.get("rank"),
                    "value": item.get("value", 0),
                })

        # 6. Bảng trend_related_queries (Truy vấn liên quan Top & Rising)
        csq = r.get("commonly_searched_queries")
        if csq and isinstance(csq, dict):
            def parse_items(container, q_type):
                raw_items = []
                if isinstance(container, list):
                    raw_items = container
                elif isinstance(container, dict):
                    for sub in container.values():
                        if isinstance(sub, list):
                            raw_items.extend(sub)
                for it in raw_items:
                    if isinstance(it, dict):
                        related_list.append({
                            "query_id": qid,
                            "query_type": q_type,
                            "related_query": clean_str(it.get("query")),
                            "rank": it.get("rank"),
                            "value": str(it.get("value", "")),
                            "is_breakout": bool(it.get("is_breakout", False)),
                            "metric_type": it.get("metric_type", "score" if q_type == "top" else "change"),
                        })

            parse_items(csq.get("top_queries"), "top")
            parse_items(csq.get("rising_queries"), "rising")

    # Chuyển đổi thành DataFrames và lưu vào các file Parquet
    df_queries = pd.DataFrame(queries_list)
    df_keywords = pd.DataFrame(keywords_list).drop_duplicates().reset_index(drop=True)
    df_timeline = pd.DataFrame(timeline_list)
    df_annual = pd.DataFrame(annual_list)
    df_regions = pd.DataFrame(regions_list)
    df_related = pd.DataFrame(related_list)

    CLEANED_QUERIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_queries.to_parquet(CLEANED_QUERIES_PATH, index=False)
    df_keywords.to_parquet(CLEANED_KEYWORDS_PATH, index=False)
    df_timeline.to_parquet(CLEANED_TIMELINE_PATH, index=False)
    df_annual.to_parquet(CLEANED_ANNUAL_PATH, index=False)
    df_regions.to_parquet(CLEANED_REGIONS_PATH, index=False)
    df_related.to_parquet(CLEANED_RELATED_PATH, index=False)

    print(f"Đã lưu trend_queries.parquet: {len(df_queries):,} dòng")
    print(f"Đã lưu trend_keywords.parquet: {len(df_keywords):,} dòng")
    print(f"Đã lưu trend_timeline.parquet: {len(df_timeline):,} dòng")
    print(f"Đã lưu trend_annual.parquet: {len(df_annual):,} dòng")
    print(f"Đã lưu trend_regions.parquet: {len(df_regions):,} dòng")
    print(f"Đã lưu trend_related_queries.parquet: {len(df_related):,} dòng")
    return df_queries, df_keywords, df_timeline, df_annual, df_regions, df_related

# ======================================================================

# export
if __name__ == "__main__":
    clean_trend_topics()
    clean_trends_json()
    print("Hoàn tất làm sạch Google Trends!")
