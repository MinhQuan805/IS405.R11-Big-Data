"""Pipeline thu thập Google Trends có lọc topic, cache và circuit breaker.

Luồng xử lý:
1. Mỗi (keyword, keyword_type) chỉ chọn một Google topic có độ liên quan cao;
   nếu không có topic đủ tốt thì dùng chính keyword.
2. Stage ``interest`` lấy Interest over time theo batch.
3. Stage ``enrichment`` chỉ lấy region và Top/Rising queries cho các query có
   tín hiệu và nằm trong giới hạn ``--max-enrich``.
4. Mỗi stage thành công được cache ngay vào SQLite. HTTP 429 làm tiến trình
   dừng sạch thay vì retry liên tục; lần chạy sau tiếp tục từ cache.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import csv
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import math
from pathlib import Path
import random
import re
import sqlite3
import sys
import time
from typing import Any, Callable, Iterable, Optional
import unicodedata


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from helpers.get_configs import get_config  # noqa: E402


TOPICS_PATH = get_config("dirs.yaml", ["raw_data", "trend_topics"], as_path=True)
TRENDS_PATH = get_config("dirs.yaml", ["raw_data", "trends"], as_path=True)
CACHE_PATH = get_config("dirs.yaml", ["raw_data", "trends_cache"], as_path=True)
LOG_PATH = get_config("dirs.yaml", ["logs", "google_trends"], as_path=True)

DEFAULT_GEO = "VI"
DEFAULT_DATE_RANGE = "all"
DEFAULT_RELEVANCE_THRESHOLD = 0.62
DEFAULT_BATCH_SIZE = 5
DEFAULT_MAX_ENRICH = 200
DEFAULT_MIN_AVERAGE_INTEREST = 0.5
DEFAULT_MIN_NONZERO_POINTS = 1
DEFAULT_REQUEST_INTERVAL = 10.0
DEFAULT_NETWORK_RETRIES = 2
CACHE_SCHEMA_VERSION = 2
MAX_GOOGLE_TERMS = 5

LOGGER = logging.getLogger("google_trends")

if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


class RateLimitReached(RuntimeError):
    """Google trả về HTTP 429; pipeline cần dừng và chờ trước khi chạy lại."""


def configure_logging(log_path: Path, verbose: bool = False) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)
    LOGGER.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    LOGGER.addHandler(console)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value))
    text = text.encode("ascii", "ignore").decode("ascii").casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def append_unique_text(values: list[str], value: str) -> None:
    if value and value.casefold() not in {item.casefold() for item in values}:
        values.append(value)


def append_unique_dict(values: list[dict[str, Any]], value: dict[str, Any]) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    existing = {
        json.dumps(item, ensure_ascii=False, sort_keys=True) for item in values
    }
    if serialized not in existing:
        values.append(value)


def topic_relevance_score(row: dict[str, str]) -> float:
    """Chấm độ liên quan keyword-title trên thang 0..1."""
    keyword = normalize_text(row.get("keyword"))
    title = normalize_text(row.get("title"))
    keyword_type = normalize_text(row.get("keyword_type"))
    topic_type = normalize_text(row.get("type"))
    if not keyword or not title:
        return 0.0
    if keyword == title:
        return 1.0

    keyword_tokens = set(keyword.split())
    title_tokens = set(title.split())
    intersection = keyword_tokens & title_tokens
    union = keyword_tokens | title_tokens
    sequence = SequenceMatcher(None, keyword, title).ratio()
    coverage = len(intersection) / len(keyword_tokens) if keyword_tokens else 0.0
    jaccard = len(intersection) / len(union) if union else 0.0
    score = 0.45 * sequence + 0.35 * coverage + 0.20 * jaccard

    if keyword in title or title in keyword:
        score += 0.10

    if keyword_type == "school":
        school_markers = ("dai hoc", "cao dang", "hoc vien", "truong")
        if any(marker in f"{title} {topic_type}" for marker in school_markers):
            score += 0.05
        noisy_markers = (
            "thu vien",
            "san bong",
            "ky tuc xa",
            "karaoke",
            "ga ",
            "van phong",
            "khoa ",
            "co so",
        )
        if any(marker in title and marker not in keyword for marker in noisy_markers):
            score -= 0.35

    return round(max(0.0, min(1.0, score)), 6)


def read_topic_rows(topics_path: Path) -> list[dict[str, str]]:
    required = {"keyword", "keyword_type", "mid", "title", "type"}
    with topics_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError(
                f"{topics_path} thiếu cột bắt buộc: {', '.join(missing)}"
            )
        rows = []
        for row in reader:
            cleaned = {key: clean_text(row.get(key)) for key in required}
            if cleaned["keyword"]:
                rows.append(cleaned)
    if not rows:
        raise ValueError(f"{topics_path} không có topic hợp lệ")
    return rows


def make_query_id(query_kind: str, query: str) -> str:
    raw = f"{query_kind}\0{query}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def select_queries(
    rows: list[dict[str, str]],
    relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    keyword_fallback: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Chọn một topic/mỗi keyword rồi gom các query trùng nhau."""
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["keyword"].casefold(), row["keyword_type"].casefold())
        scored = {**row, "relevance_score": topic_relevance_score(row)}
        candidates.setdefault(key, []).append(scored)

    selected: list[dict[str, Any]] = []
    rejected_pairs = 0
    fallback_pairs = 0
    for group in candidates.values():
        best = max(
            group,
            key=lambda item: (
                item["relevance_score"],
                -len(item["title"]),
                item["mid"],
            ),
        )
        use_mid = bool(best["mid"]) and best["relevance_score"] >= relevance_threshold
        if use_mid:
            query = best["mid"]
            query_kind = "topic_mid"
            reason = "best_relevant_topic"
        elif keyword_fallback:
            query = best["keyword"]
            query_kind = "search_term"
            reason = "keyword_fallback"
            fallback_pairs += 1
        else:
            rejected_pairs += 1
            continue
        selected.append(
            {
                **best,
                "query": query,
                "query_kind": query_kind,
                "selection_reason": reason,
                "candidate_count": len(group),
            }
        )

    task_map: dict[tuple[str, str], dict[str, Any]] = {}
    for item in selected:
        normalized_query = (
            item["query"]
            if item["query_kind"] == "topic_mid"
            else normalize_text(item["query"])
        )
        key = (item["query_kind"], normalized_query)
        if key not in task_map:
            task_map[key] = {
                "query_id": make_query_id(item["query_kind"], item["query"]),
                "query": item["query"],
                "query_kind": item["query_kind"],
                "mid": item["mid"] if item["query_kind"] == "topic_mid" else None,
                "keyword": item["keyword"],
                "keyword_type": item["keyword_type"],
                "keywords": [],
                "keyword_types": [],
                "keyword_metadata": [],
                "title": item["title"] if item["query_kind"] == "topic_mid" else "",
                "type": item["type"] if item["query_kind"] == "topic_mid" else "",
                "selection_score": item["relevance_score"],
            }
        task = task_map[key]
        append_unique_text(task["keywords"], item["keyword"])
        append_unique_text(task["keyword_types"], item["keyword_type"])
        task["selection_score"] = max(
            task["selection_score"], item["relevance_score"]
        )
        append_unique_dict(
            task["keyword_metadata"],
            {
                "keyword": item["keyword"],
                "keyword_type": item["keyword_type"],
                "selected_mid": item["mid"] or None,
                "selected_title": item["title"],
                "selected_type": item["type"],
                "relevance_score": item["relevance_score"],
                "selection_reason": item["selection_reason"],
                "candidate_count": item["candidate_count"],
            },
        )

    tasks = list(task_map.values())
    stats = {
        "source_rows": len(rows),
        "source_keyword_pairs": len(candidates),
        "selected_topic_pairs": sum(
            item["query_kind"] == "topic_mid" for item in selected
        ),
        "keyword_fallback_pairs": fallback_pairs,
        "rejected_keyword_pairs": rejected_pairs,
        "unique_queries": len(tasks),
        "unique_topic_mids": sum(task["query_kind"] == "topic_mid" for task in tasks),
        "unique_search_terms": sum(
            task["query_kind"] == "search_term" for task in tasks
        ),
    }
    return tasks, stats


def chunked(values: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def stable_signature(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def initialize_cache(cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(cache_path)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS trend_cache (
                cache_key TEXT PRIMARY KEY,
                signature TEXT NOT NULL,
                stage TEXT NOT NULL,
                query_id TEXT NOT NULL,
                query_text TEXT NOT NULL,
                query_kind TEXT NOT NULL,
                geo TEXT NOT NULL,
                date_range TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_trend_cache_lookup "
            "ON trend_cache(signature, stage, geo, date_range)"
        )
        connection.commit()


def make_cache_key(
    signature: str,
    stage: str,
    task: dict[str, Any],
    geo: str,
    date_range: str,
) -> str:
    return stable_signature(
        [CACHE_SCHEMA_VERSION, signature, stage, task["query_id"], geo, date_range]
    )


def load_stage_cache(
    cache_path: Path,
    signature: str,
    stage: str,
    geo: str,
    date_range: str,
) -> dict[str, dict[str, Any]]:
    with closing(sqlite3.connect(cache_path)) as connection:
        rows = connection.execute(
            """
            SELECT query_id, payload_json
            FROM trend_cache
            WHERE signature = ? AND stage = ? AND geo = ? AND date_range = ?
            """,
            (signature, stage, geo, date_range),
        ).fetchall()
    cache = {}
    for query_id, payload_json in rows:
        try:
            cache[query_id] = json.loads(payload_json)
        except json.JSONDecodeError:
            LOGGER.warning("Bỏ cache JSON hỏng cho query_id=%s", query_id)
    return cache


def save_stage_cache(
    cache_path: Path,
    signature: str,
    stage: str,
    geo: str,
    date_range: str,
    items: list[tuple[dict[str, Any], dict[str, Any]]],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    records = [
        (
            make_cache_key(signature, stage, task, geo, date_range),
            signature,
            stage,
            task["query_id"],
            task["query"],
            task["query_kind"],
            geo,
            date_range,
            json.dumps(payload, ensure_ascii=False, allow_nan=False),
            now,
        )
        for task, payload in items
    ]
    with closing(sqlite3.connect(cache_path)) as connection:
        connection.executemany(
            """
            INSERT INTO trend_cache (
                cache_key, signature, stage, query_id, query_text, query_kind,
                geo, date_range, payload_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            records,
        )
        connection.commit()


def clear_cache(cache_path: Path) -> None:
    if cache_path.exists():
        cache_path.unlink()
    for suffix in ("-shm", "-wal"):
        sidecar = Path(f"{cache_path}{suffix}")
        if sidecar.exists():
            sidecar.unlink()


def import_trend_client() -> tuple[type[Any], str]:
    try:
        from pytrends_modern import TrendReq

        return TrendReq, "pytrends-modern"
    except ImportError:
        try:
            from pytrends.request import TrendReq

            return TrendReq, "pytrends"
        except ImportError as error:
            raise RuntimeError(
                "Chưa cài Google Trends client. Chạy: pip install -r requirements.txt"
            ) from error


def create_rate_limiter(min_interval: float) -> dict[str, float]:
    return {"min_interval": max(0.0, min_interval), "last_request": 0.0}


def wait_for_request(rate_limiter: dict[str, float]) -> None:
    interval = rate_limiter["min_interval"]
    now = time.monotonic()
    delay = interval - (now - rate_limiter["last_request"])
    if delay > 0:
        time.sleep(delay + random.uniform(0.0, min(1.0, interval * 0.1)))
    rate_limiter["last_request"] = time.monotonic()


def wrap_client_rate_limit(client: Any, rate_limiter: dict[str, float]) -> bool:
    original = getattr(client, "_get_data", None)
    if not callable(original):
        return False

    def limited_get_data(*args: Any, **kwargs: Any) -> Any:
        wait_for_request(rate_limiter)
        return original(*args, **kwargs)

    client._get_data = limited_get_data
    return True


def get_client(
    holder: dict[str, Any], rate_limiter: dict[str, float]
) -> tuple[Any, str, bool]:
    if holder.get("client") is None:
        client_type, backend = import_trend_client()
        client = client_type(
            hl="vi-VN",
            tz=-420,
            timeout=(10, 30),
            retries=0,
            backoff_factor=0,
        )
        holder.update(
            client=client,
            backend=backend,
            wrapped=wrap_client_rate_limit(client, rate_limiter),
        )
    return holder["client"], holder["backend"], holder["wrapped"]


def reset_client(holder: dict[str, Any]) -> None:
    client = holder.pop("client", None)
    session = getattr(client, "session", None)
    if session is not None and hasattr(session, "close"):
        session.close()
    holder.pop("backend", None)
    holder.pop("wrapped", None)


def call_client(
    function: Callable[..., Any],
    rate_limiter: dict[str, float],
    wrapped: bool,
    *args: Any,
    **kwargs: Any,
) -> Any:
    if not wrapped:
        wait_for_request(rate_limiter)
    return function(*args, **kwargs)


def is_rate_limit_error(error: BaseException) -> bool:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    message = str(error).casefold()
    return status == 429 or "429" in message or "quota limit" in message or "rate limit" in message


def is_retryable_network_error(error: BaseException) -> bool:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status >= 500 or status in {408, 425}
    message = str(error).casefold()
    markers = ("timeout", "timed out", "connection", "502", "503", "504")
    return any(marker in message for marker in markers)


def execute_with_retry(
    operation: Callable[[], Any],
    label: str,
    holder: dict[str, Any],
    max_retries: int,
) -> Any:
    for attempt in range(1, max_retries + 2):
        try:
            return operation()
        except KeyboardInterrupt:
            raise
        except Exception as error:
            reset_client(holder)
            if is_rate_limit_error(error):
                raise RateLimitReached(
                    "Google trả về HTTP 429. Pipeline đã dừng sạch; "
                    "hãy chờ rồi chạy lại để tiếp tục từ cache."
                ) from error
            if attempt > max_retries or not is_retryable_network_error(error):
                raise
            delay = min(60.0, 5.0 * (2 ** (attempt - 1))) + random.uniform(0, 1)
            LOGGER.warning(
                "%s lỗi mạng (%s/%s): %s; retry sau %.1fs",
                label,
                attempt,
                max_retries + 1,
                error,
                delay,
            )
            time.sleep(delay)


def to_scalar(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def parse_interest_frame(
    frame: Any,
    query: str,
    backend: str,
    request_terms: list[str],
) -> dict[str, Any]:
    timeline = []
    numeric_values: list[float] = []
    if frame is not None and not frame.empty and query in frame.columns:
        for date_value, raw_value in frame[query].items():
            value = to_scalar(raw_value)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                value = int(value) if float(value).is_integer() else float(value)
                numeric_values.append(float(value))
                date_text = (
                    date_value.isoformat()
                    if hasattr(date_value, "isoformat")
                    else str(date_value)
                )
                timeline.append({"date": date_text, "value": value})
    return {
        "timeline": timeline,
        "average_interest": (
            round(sum(numeric_values) / len(numeric_values), 4)
            if numeric_values
            else 0.0
        ),
        "max_interest": max(numeric_values, default=0.0),
        "nonzero_points": sum(value > 0 for value in numeric_values),
        "data_source": backend,
        "request_terms": request_terms,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_regions(frame: Any, query: str) -> list[dict[str, Any]]:
    regions = []
    if frame is not None and not frame.empty and query in frame.columns:
        for region, raw_value in frame[query].items():
            value = to_scalar(raw_value)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                regions.append({"region": str(region), "value": value})
    regions.sort(key=lambda item: item["value"], reverse=True)
    for rank, item in enumerate(regions, start=1):
        item["rank"] = rank
    return regions


def dataframe_rows(frame: Any) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    return frame.to_dict("records")


def parse_query_rows(frame: Any, rising: bool) -> list[dict[str, Any]]:
    results = []
    for rank, row in enumerate(dataframe_rows(frame), start=1):
        raw_value = to_scalar(row.get("value"))
        formatted = to_scalar(row.get("formattedValue", row.get("formatted_value")))
        value = formatted if formatted not in (None, "") else raw_value
        results.append(
            {
                "rank": rank,
                "query": clean_text(row.get("query")),
                "value": value,
                "is_breakout": (
                    str(value or "").casefold() == "breakout"
                    or (
                        rising
                        and isinstance(raw_value, (int, float))
                        and not isinstance(raw_value, bool)
                        and raw_value >= 5000
                    )
                ),
            }
        )
    return results


def parse_related(related: Any, query: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    query_data = related.get(query) if isinstance(related, dict) else None
    query_data = query_data if isinstance(query_data, dict) else {}
    return (
        parse_query_rows(query_data.get("top"), rising=False),
        parse_query_rows(query_data.get("rising"), rising=True),
    )


def fetch_interest_batch(
    batch: list[dict[str, Any]],
    anchor: str,
    geo: str,
    date_range: str,
    holder: dict[str, Any],
    rate_limiter: dict[str, float],
    max_retries: int,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    queries = [task["query"] for task in batch]
    request_terms = ([anchor] if anchor else []) + queries

    def operation() -> list[tuple[dict[str, Any], dict[str, Any]]]:
        client, backend, wrapped = get_client(holder, rate_limiter)
        call_client(
            client.build_payload,
            rate_limiter,
            wrapped,
            kw_list=request_terms,
            timeframe=date_range,
            geo=geo,
        )
        frame = call_client(client.interest_over_time, rate_limiter, wrapped)
        return [
            (task, parse_interest_frame(frame, task["query"], backend, request_terms))
            for task in batch
        ]

    return execute_with_retry(
        operation,
        f"Interest batch {queries}",
        holder,
        max_retries,
    )


def fetch_enrichment_batch(
    batch: list[dict[str, Any]],
    geo: str,
    date_range: str,
    holder: dict[str, Any],
    rate_limiter: dict[str, float],
    max_retries: int,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    queries = [task["query"] for task in batch]

    def operation() -> list[tuple[dict[str, Any], dict[str, Any]]]:
        client, backend, wrapped = get_client(holder, rate_limiter)
        call_client(
            client.build_payload,
            rate_limiter,
            wrapped,
            kw_list=queries,
            timeframe=date_range,
            geo=geo,
        )
        region_frame = call_client(
            client.interest_by_region,
            rate_limiter,
            wrapped,
            resolution="REGION",
            inc_low_vol=True,
        )
        related = call_client(client.related_queries, rate_limiter, wrapped)
        collected_at = datetime.now(timezone.utc).isoformat()
        results = []
        for task in batch:
            top_queries, rising_queries = parse_related(related, task["query"])
            results.append(
                (
                    task,
                    {
                        "interest_by_region": {
                            "regions": parse_regions(region_frame, task["query"]),
                            "data_source": backend,
                        },
                        "commonly_searched_queries": {
                            "top_queries": top_queries,
                            "rising_queries": rising_queries,
                            "data_source": backend,
                        },
                        "request_terms": queries,
                        "collected_at": collected_at,
                    },
                )
            )
        return results

    return execute_with_retry(
        operation,
        f"Enrichment batch {queries}",
        holder,
        max_retries,
    )


def run_interest_stage(
    tasks: list[dict[str, Any]],
    cache_path: Path,
    signature: str,
    interest_cache: dict[str, dict[str, Any]],
    batch_size: int,
    anchor: str,
    geo: str,
    date_range: str,
    holder: dict[str, Any],
    rate_limiter: dict[str, float],
    max_retries: int,
    runtime_errors: dict[str, list[str]],
) -> bool:
    batches = list(chunked(tasks, batch_size))
    completed_batches = 0
    for index, batch in enumerate(batches, start=1):
        if all(task["query_id"] in interest_cache for task in batch):
            completed_batches += 1
            continue
        try:
            items = fetch_interest_batch(
                batch,
                anchor,
                geo,
                date_range,
                holder,
                rate_limiter,
                max_retries,
            )
        except RateLimitReached:
            raise
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            LOGGER.error("Interest batch %s/%s thất bại: %s", index, len(batches), message)
            for task in batch:
                runtime_errors.setdefault(task["query_id"], []).append(message)
            continue

        save_stage_cache(cache_path, signature, "interest", geo, date_range, items)
        for task, payload in items:
            interest_cache[task["query_id"]] = payload
        completed_batches += 1
        LOGGER.info(
            "Interest %s/%s batch | cache=%s/%s queries",
            index,
            len(batches),
            len(interest_cache),
            len(tasks),
        )
    return completed_batches == len(batches)


def select_enrichment_tasks(
    tasks: list[dict[str, Any]],
    interest_cache: dict[str, dict[str, Any]],
    min_average_interest: float,
    min_nonzero_points: int,
    max_enrich: int,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    eligible = []
    reasons: dict[str, str] = {}
    for task in tasks:
        interest = interest_cache.get(task["query_id"])
        if interest is None:
            reasons[task["query_id"]] = "interest_pending"
            continue
        if (
            interest.get("average_interest", 0) < min_average_interest
            or interest.get("nonzero_points", 0) < min_nonzero_points
        ):
            reasons[task["query_id"]] = "low_interest"
            continue
        eligible.append(task)

    eligible.sort(
        key=lambda task: (
            task.get("selection_score", 0),
            interest_cache[task["query_id"]].get("average_interest", 0),
            interest_cache[task["query_id"]].get("max_interest", 0),
        ),
        reverse=True,
    )
    selected = eligible[:max_enrich] if max_enrich > 0 else eligible
    selected_ids = {task["query_id"] for task in selected}
    for task in eligible:
        if task["query_id"] not in selected_ids:
            reasons[task["query_id"]] = "enrichment_limit"
    return selected, reasons


def run_enrichment_stage(
    tasks: list[dict[str, Any]],
    cache_path: Path,
    signature: str,
    enrichment_cache: dict[str, dict[str, Any]],
    batch_size: int,
    geo: str,
    date_range: str,
    holder: dict[str, Any],
    rate_limiter: dict[str, float],
    max_retries: int,
    runtime_errors: dict[str, list[str]],
) -> bool:
    batches = list(chunked(tasks, batch_size))
    completed_batches = 0
    for index, batch in enumerate(batches, start=1):
        if all(task["query_id"] in enrichment_cache for task in batch):
            completed_batches += 1
            continue
        try:
            items = fetch_enrichment_batch(
                batch,
                geo,
                date_range,
                holder,
                rate_limiter,
                max_retries,
            )
        except RateLimitReached:
            raise
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            LOGGER.error("Enrichment batch %s/%s thất bại: %s", index, len(batches), message)
            for task in batch:
                runtime_errors.setdefault(task["query_id"], []).append(message)
            continue

        save_stage_cache(cache_path, signature, "enrichment", geo, date_range, items)
        for task, payload in items:
            enrichment_cache[task["query_id"]] = payload
        completed_batches += 1
        LOGGER.info(
            "Enrichment %s/%s batch | cache=%s/%s queries",
            index,
            len(batches),
            len(enrichment_cache),
            len(tasks),
        )
    return completed_batches == len(batches)


def assemble_records(
    tasks: list[dict[str, Any]],
    interest_cache: dict[str, dict[str, Any]],
    enrichment_cache: dict[str, dict[str, Any]],
    enrichment_reasons: dict[str, str],
    selected_enrichment_ids: set[str],
    runtime_errors: dict[str, list[str]],
    geo: str,
    date_range: str,
) -> list[dict[str, Any]]:
    records = []
    for task in tasks:
        query_id = task["query_id"]
        interest = interest_cache.get(query_id)
        enrichment = enrichment_cache.get(query_id)
        if interest is None:
            status = "pending"
        elif enrichment is not None:
            status = "success"
        elif query_id in selected_enrichment_ids:
            status = "enrichment_pending"
        else:
            status = "interest_only"

        reason = enrichment_reasons.get(query_id)
        records.append(
            {
                **task,
                "geo": geo,
                "date_range": date_range,
                "status": status,
                "stage_status": {
                    "interest": "success" if interest is not None else "pending",
                    "enrichment": (
                        "success"
                        if enrichment is not None
                        else "pending"
                        if query_id in selected_enrichment_ids
                        else "skipped"
                    ),
                    "enrichment_skip_reason": reason,
                },
                "errors": runtime_errors.get(query_id, []),
                "interest_over_time": interest,
                "interest_by_region": (
                    enrichment.get("interest_by_region") if enrichment else None
                ),
                "commonly_searched_queries": (
                    enrichment.get("commonly_searched_queries") if enrichment else None
                ),
            }
        )
    return records


def atomic_write_json(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(records, target, ensure_ascii=False, indent=2, allow_nan=False)
        target.write("\n")
        target.flush()
    temporary.replace(output_path)


def validate_options(batch_size: int, anchor: str, max_retries: int) -> None:
    if batch_size < 1:
        raise ValueError("batch-size phải >= 1")
    if batch_size + (1 if anchor else 0) > MAX_GOOGLE_TERMS:
        raise ValueError(
            f"Google hỗ trợ tối đa {MAX_GOOGLE_TERMS} terms; "
            "hãy giảm batch-size hoặc bỏ anchor"
        )
    if max_retries < 0:
        raise ValueError("max-network-retries phải >= 0")


def run_pipeline(
    topics_path: Path = TOPICS_PATH,
    output_path: Path = TRENDS_PATH,
    cache_path: Path = CACHE_PATH,
    geo: str = DEFAULT_GEO,
    date_range: str = DEFAULT_DATE_RANGE,
    stage: str = "all",
    relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD,
    keyword_fallback: bool = True,
    batch_size: int = DEFAULT_BATCH_SIZE,
    anchor: str = "",
    max_enrich: int = DEFAULT_MAX_ENRICH,
    min_average_interest: float = DEFAULT_MIN_AVERAGE_INTEREST,
    min_nonzero_points: int = DEFAULT_MIN_NONZERO_POINTS,
    min_request_interval: float = DEFAULT_REQUEST_INTERVAL,
    max_network_retries: int = DEFAULT_NETWORK_RETRIES,
    limit: Optional[int] = None,
) -> tuple[list[dict[str, Any]], str]:
    anchor = clean_text(anchor)
    validate_options(batch_size, anchor, max_network_retries)
    rows = read_topic_rows(topics_path)
    tasks, selection_stats = select_queries(
        rows,
        relevance_threshold=relevance_threshold,
        keyword_fallback=keyword_fallback,
    )
    if limit is not None:
        tasks = tasks[: max(0, limit)]
    LOGGER.info("Topic selection: %s", selection_stats)
    LOGGER.info("Sẽ xử lý %s query duy nhất", len(tasks))

    initialize_cache(cache_path)
    interest_signature = stable_signature(
        {
            "schema": CACHE_SCHEMA_VERSION,
            "queries": [task["query_id"] for task in tasks],
            "batch_size": batch_size,
            "anchor": anchor,
        }
    )
    interest_cache = load_stage_cache(
        cache_path, interest_signature, "interest", geo, date_range
    )
    holder: dict[str, Any] = {}
    rate_limiter = create_rate_limiter(min_request_interval)
    runtime_errors: dict[str, list[str]] = {}
    stopped_reason = "completed"

    enrichment_tasks: list[dict[str, Any]] = []
    enrichment_reasons: dict[str, str] = {}
    enrichment_cache: dict[str, dict[str, Any]] = {}
    enrichment_signature = ""
    interest_complete = len(interest_cache) == len(tasks)

    try:
        if stage in {"all", "interest"}:
            interest_complete = run_interest_stage(
                tasks,
                cache_path,
                interest_signature,
                interest_cache,
                batch_size,
                anchor,
                geo,
                date_range,
                holder,
                rate_limiter,
                max_network_retries,
                runtime_errors,
            )

        enrichment_tasks, enrichment_reasons = select_enrichment_tasks(
            tasks,
            interest_cache,
            min_average_interest,
            min_nonzero_points,
            max_enrich,
        )
        enrichment_signature = stable_signature(
            {
                "schema": CACHE_SCHEMA_VERSION,
                "queries": [task["query_id"] for task in enrichment_tasks],
                "batch_size": batch_size,
            }
        )
        enrichment_cache = load_stage_cache(
            cache_path, enrichment_signature, "enrichment", geo, date_range
        )

        if stage in {"all", "enrichment"}:
            if not interest_complete:
                LOGGER.warning(
                    "Interest stage chưa hoàn tất; chưa chạy enrichment để giữ shortlist ổn định"
                )
                stopped_reason = "interest_incomplete"
            elif enrichment_tasks:
                run_enrichment_stage(
                    enrichment_tasks,
                    cache_path,
                    enrichment_signature,
                    enrichment_cache,
                    batch_size,
                    geo,
                    date_range,
                    holder,
                    rate_limiter,
                    max_network_retries,
                    runtime_errors,
                )
    except RateLimitReached as error:
        stopped_reason = "rate_limited"
        LOGGER.error("%s", error)
    except KeyboardInterrupt:
        stopped_reason = "interrupted"
        LOGGER.warning("Đã nhận Ctrl+C; đang ghi JSON từ cache, không chờ worker nền")
    finally:
        reset_client(holder)

    selected_enrichment_ids = {task["query_id"] for task in enrichment_tasks}
    records = assemble_records(
        tasks,
        interest_cache,
        enrichment_cache,
        enrichment_reasons,
        selected_enrichment_ids,
        runtime_errors,
        geo,
        date_range,
    )
    atomic_write_json(records, output_path)
    LOGGER.info(
        "Đã ghi %s objects vào %s | interest=%s | enriched=%s | stop=%s",
        len(records),
        output_path,
        len(interest_cache),
        len(enrichment_cache),
        stopped_reason,
    )
    return records, stopped_reason


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Google Trends pipeline: filter -> interest -> selective enrichment."
    )
    parser.add_argument("--input", type=Path, default=TOPICS_PATH)
    parser.add_argument("--output", type=Path, default=TRENDS_PATH)
    parser.add_argument("--cache", type=Path, default=CACHE_PATH)
    parser.add_argument("--geo", default=DEFAULT_GEO)
    parser.add_argument("--date", dest="date_range", default=DEFAULT_DATE_RANGE)
    parser.add_argument("--stage", choices=("all", "interest", "enrichment"), default="all")
    parser.add_argument("--relevance-threshold", type=float, default=DEFAULT_RELEVANCE_THRESHOLD)
    parser.add_argument("--no-keyword-fallback", action="store_true")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--anchor", default="")
    parser.add_argument("--max-enrich", type=int, default=DEFAULT_MAX_ENRICH)
    parser.add_argument("--min-average-interest", type=float, default=DEFAULT_MIN_AVERAGE_INTEREST)
    parser.add_argument("--min-nonzero-points", type=int, default=DEFAULT_MIN_NONZERO_POINTS)
    parser.add_argument("--min-request-interval", type=float, default=DEFAULT_REQUEST_INTERVAL)
    parser.add_argument("--max-network-retries", type=int, default=DEFAULT_NETWORK_RETRIES)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--clear-cache", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(LOG_PATH, verbose=args.verbose)

    try:
        rows = read_topic_rows(args.input)
        tasks, stats = select_queries(
            rows,
            relevance_threshold=args.relevance_threshold,
            keyword_fallback=not args.no_keyword_fallback,
        )
        if args.limit is not None:
            tasks = tasks[: max(0, args.limit)]
        if args.clear_cache:
            clear_cache(args.cache)
            LOGGER.info("Đã xóa cache %s", args.cache)
        if args.validate_only:
            print(json.dumps({**stats, "queries_after_limit": len(tasks)}, ensure_ascii=False, indent=2))
            print("Không có request nào được gửi đến Google Trends.")
            return 0

        _, stopped_reason = run_pipeline(
            topics_path=args.input,
            output_path=args.output,
            cache_path=args.cache,
            geo=args.geo,
            date_range=args.date_range,
            stage=args.stage,
            relevance_threshold=args.relevance_threshold,
            keyword_fallback=not args.no_keyword_fallback,
            batch_size=args.batch_size,
            anchor=args.anchor,
            max_enrich=args.max_enrich,
            min_average_interest=args.min_average_interest,
            min_nonzero_points=args.min_nonzero_points,
            min_request_interval=args.min_request_interval,
            max_network_retries=args.max_network_retries,
            limit=args.limit,
        )
    except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
        LOGGER.error("Pipeline dừng: %s", error)
        return 1
    if stopped_reason == "interrupted":
        return 130
    if stopped_reason == "rate_limited":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
