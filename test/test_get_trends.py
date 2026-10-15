"""Kiểm thử offline cho pipeline Google Trends; không gọi mạng."""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts-fetching" / "unit-scripts" / "get_trends.py"
SPEC = importlib.util.spec_from_file_location("get_trends", MODULE_PATH)
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(pipeline)


def topic_row(
    keyword: str,
    keyword_type: str,
    mid: str,
    title: str,
    topic_type: str = "Chủ đề",
) -> dict[str, str]:
    return {
        "keyword": keyword,
        "keyword_type": keyword_type,
        "mid": mid,
        "title": title,
        "type": topic_type,
    }


class GoogleTrendsPipelineTests(unittest.TestCase):
    def test_school_noise_is_penalized(self) -> None:
        exact = topic_row(
            "Đại học Bách Khoa Hà Nội",
            "school",
            "/m/school",
            "Đại học Bách Khoa Hà Nội",
            "Trường đại học",
        )
        noisy = topic_row(
            "Đại học Bách Khoa Hà Nội",
            "school",
            "/m/library",
            "Thư viện Đại học Bách Khoa Hà Nội",
            "Thư viện",
        )
        self.assertGreater(
            pipeline.topic_relevance_score(exact),
            pipeline.topic_relevance_score(noisy),
        )

    def test_selects_one_mid_or_keyword_fallback_per_keyword(self) -> None:
        rows = [
            topic_row("Khoa học dữ liệu", "major", "/m/good", "Khoa học dữ liệu"),
            topic_row("Khoa học dữ liệu", "major", "/m/bad", "Nhà hàng"),
            topic_row("Tổ hợp lạ", "subject_group", "/m/other", "Bóng đá"),
        ]
        tasks, stats = pipeline.select_queries(rows, relevance_threshold=0.62)

        by_keyword = {task["keyword"]: task for task in tasks}
        self.assertEqual(by_keyword["Khoa học dữ liệu"]["query"], "/m/good")
        self.assertEqual(by_keyword["Khoa học dữ liệu"]["query_kind"], "topic_mid")
        self.assertEqual(by_keyword["Tổ hợp lạ"]["query"], "Tổ hợp lạ")
        self.assertEqual(by_keyword["Tổ hợp lạ"]["query_kind"], "search_term")
        self.assertEqual(stats["source_keyword_pairs"], 2)
        self.assertEqual(stats["unique_queries"], 2)

    def test_cache_round_trip(self) -> None:
        task = {
            "query_id": "query-1",
            "query": "/m/topic",
            "query_kind": "topic_mid",
        }
        payload = {"average_interest": 12.5, "timeline": []}
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "cache.sqlite3"
            pipeline.initialize_cache(cache_path)
            pipeline.save_stage_cache(
                cache_path,
                "signature",
                "interest",
                "VN",
                "all",
                [(task, payload)],
            )
            cached = pipeline.load_stage_cache(
                cache_path, "signature", "interest", "VN", "all"
            )

        self.assertEqual(cached["query-1"], payload)

    def test_parse_interest_frame(self) -> None:
        frame = pd.DataFrame(
            {"/m/topic": [0, 10, 20], "isPartial": [False, False, False]},
            index=pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"]),
        )
        parsed = pipeline.parse_interest_frame(
            frame, "/m/topic", "pytrends-modern", ["/m/topic"]
        )
        self.assertEqual(parsed["average_interest"], 10.0)
        self.assertEqual(parsed["max_interest"], 20.0)
        self.assertEqual(parsed["nonzero_points"], 2)
        self.assertEqual(len(parsed["timeline"]), 3)

    def test_enrichment_shortlist_is_limited_and_ranked(self) -> None:
        tasks = [
            {"query_id": "low"},
            {"query_id": "medium"},
            {"query_id": "high"},
        ]
        interest = {
            "low": {"average_interest": 0.0, "nonzero_points": 0, "max_interest": 0},
            "medium": {"average_interest": 10.0, "nonzero_points": 2, "max_interest": 20},
            "high": {"average_interest": 30.0, "nonzero_points": 3, "max_interest": 80},
        }
        selected, reasons = pipeline.select_enrichment_tasks(
            tasks,
            interest,
            min_average_interest=0.5,
            min_nonzero_points=1,
            max_enrich=1,
        )
        self.assertEqual([task["query_id"] for task in selected], ["high"])
        self.assertEqual(reasons["low"], "low_interest")
        self.assertEqual(reasons["medium"], "enrichment_limit")

    def test_rate_limit_detection(self) -> None:
        self.assertTrue(
            pipeline.is_rate_limit_error(
                RuntimeError("You have reached your quota limit")
            )
        )
        self.assertFalse(pipeline.is_rate_limit_error(RuntimeError("bad payload")))

    def test_pipeline_end_to_end_uses_cache_and_writes_one_json_array(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            topics_path = root / "topics.csv"
            output_path = root / "trends.json"
            cache_path = root / "cache.sqlite3"
            with topics_path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(
                    target,
                    fieldnames=["keyword", "keyword_type", "mid", "title", "type"],
                )
                writer.writeheader()
                writer.writerow(
                    topic_row(
                        "Khoa học dữ liệu",
                        "major",
                        "/m/data",
                        "Khoa học dữ liệu",
                    )
                )

            def fake_interest(batch, *args, **kwargs):
                return [
                    (
                        task,
                        {
                            "timeline": [{"date": "2026-01-01", "value": 50}],
                            "average_interest": 50.0,
                            "max_interest": 50.0,
                            "nonzero_points": 1,
                            "data_source": "fake",
                            "request_terms": [task["query"]],
                            "collected_at": "2026-10-13T00:00:00+00:00",
                        },
                    )
                    for task in batch
                ]

            def fake_enrichment(batch, *args, **kwargs):
                return [
                    (
                        task,
                        {
                            "interest_by_region": {"regions": [], "data_source": "fake"},
                            "commonly_searched_queries": {
                                "top_queries": [],
                                "rising_queries": [],
                                "data_source": "fake",
                            },
                            "request_terms": [task["query"]],
                            "collected_at": "2026-10-13T00:00:00+00:00",
                        },
                    )
                    for task in batch
                ]

            with patch.object(pipeline, "fetch_interest_batch", side_effect=fake_interest), patch.object(
                pipeline, "fetch_enrichment_batch", side_effect=fake_enrichment
            ):
                records, stopped = pipeline.run_pipeline(
                    topics_path=topics_path,
                    output_path=output_path,
                    cache_path=cache_path,
                    geo="VN",
                    date_range="all",
                    stage="all",
                    min_request_interval=0,
                    max_network_retries=0,
                )

            with output_path.open("r", encoding="utf-8") as source:
                stored = json.load(source)

        self.assertEqual(stopped, "completed")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "success")
        self.assertIsInstance(stored, list)
        self.assertEqual(stored[0]["query"], "/m/data")

    def test_rate_limit_stops_cleanly_and_writes_pending_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            topics_path = root / "topics.csv"
            output_path = root / "trends.json"
            cache_path = root / "cache.sqlite3"
            with topics_path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(
                    target,
                    fieldnames=["keyword", "keyword_type", "mid", "title", "type"],
                )
                writer.writeheader()
                writer.writerow(
                    topic_row("Dữ liệu lớn", "major", "/m/big-data", "Dữ liệu lớn")
                )

            with patch.object(
                pipeline,
                "fetch_interest_batch",
                side_effect=pipeline.RateLimitReached("HTTP 429"),
            ):
                records, stopped = pipeline.run_pipeline(
                    topics_path=topics_path,
                    output_path=output_path,
                    cache_path=cache_path,
                    geo="VN",
                    stage="all",
                    min_request_interval=0,
                    max_network_retries=0,
                )

        self.assertEqual(stopped, "rate_limited")
        self.assertEqual(records[0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
