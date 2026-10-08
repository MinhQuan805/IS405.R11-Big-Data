import os
import yaml
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd
from tqdm import tqdm

from src.utils.logger import setup_logger
from src.scraper.trends_client import RobustTrendsClient
from src.scraper.normalizer import AnchorNormalizer
from src.storage.lake_manager import DataLakeManager

class GoogleTrendsPipeline:
    """
    Pipeline thu thập dữ liệu Google Trends tự động, tối ưu hóa:
    - Đọc cấu hình từ file YAML
    - Gom nhóm batch tối đa 5 từ khóa (bao gồm Anchor Keyword mốc chuẩn)
    - Thu thập chuỗi thời gian, vùng miền, related queries
    - Tự động chuẩn hóa tỷ lệ chéo (Anchor Normalization)
    - Lưu trữ phân vùng Data Lake (Parquet/CSV) và nạp DuckDB Warehouse
    """
    def __init__(
        self,
        config_path: str = "config/scraper_config.yaml",
        keywords_path: str = "config/keywords_it.yaml",
        timeframe: Optional[str] = None
    ):
        self.logger = setup_logger("GoogleTrendsPipeline")
        self.config = self._load_yaml(config_path)
        self.keywords_config = self._load_yaml(keywords_path)

        # Cấu hình Google Trends
        gt_cfg = self.config.get("google_trends", {})
        self.hl = gt_cfg.get("hl", "vi-VN")
        self.tz = gt_cfg.get("tz", 420)
        self.geo = gt_cfg.get("geo", "VN")
        self.cat = gt_cfg.get("cat", 0)

        # Xử lý timeframe linh hoạt (1y, 3m, 5y)
        tf_input = str(timeframe or gt_cfg.get("timeframe", "today 5-y")).strip().lower()
        if tf_input in ["1y", "1year", "12m", "today 12-m"]:
            self.timeframe = "today 12-m"
            self.timeframe_suffix = "1y"
        elif tf_input in ["3m", "3month", "90d", "today 3-m"]:
            self.timeframe = "today 3-m"
            self.timeframe_suffix = "3m"
        elif tf_input in ["5y", "5year", "today 5-y"]:
            self.timeframe = "today 5-y"
            self.timeframe_suffix = "5y"
        else:
            self.timeframe = tf_input
            self.timeframe_suffix = tf_input.replace(" ", "_").replace("-", "").replace("/", "")[:6]

        self.logger.info(f"Cấu hình khung thời gian: '{self.timeframe}' (hậu tố: '_{self.timeframe_suffix}')")

        # Cấu hình Rate limit
        rl_cfg = self.config.get("rate_limit", {})
        self.client = RobustTrendsClient(
            hl=self.hl,
            tz=self.tz,
            min_delay=rl_cfg.get("min_delay_sec", 1.5),
            max_delay=rl_cfg.get("max_delay_sec", 3.0),
            max_retries=rl_cfg.get("max_retries", 5),
            backoff_base=rl_cfg.get("backoff_base_sec", 10.0),
            logger=self.logger
        )

        # Cấu hình Feature Flags (Fast Mode)
        feat_cfg = self.config.get("features", {})
        self.fetch_over_time = feat_cfg.get("fetch_interest_over_time", True)
        self.fetch_by_region = feat_cfg.get("fetch_interest_by_region", True)
        self.fetch_related = feat_cfg.get("fetch_related_queries", False)

        # Cấu hình Storage & Normalizer
        st_cfg = self.config.get("storage", {})
        self.lake_manager = DataLakeManager(
            raw_dir=st_cfg.get("lake_raw_dir", "data/lake/raw"),
            normalized_dir=st_cfg.get("lake_normalized_dir", "data/lake/normalized"),
            duckdb_path=st_cfg.get("warehouse_duckdb_path", "data/warehouse/trends.duckdb"),
            logger=self.logger
        )

        self.anchor = self.keywords_config.get("anchor_keyword", "Công nghệ thông tin")
        self.normalizer = AnchorNormalizer(self.anchor, logger=self.logger)
        self.enable_duckdb = st_cfg.get("enable_duckdb_sync", True)

    def _load_yaml(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _create_batches(self, keywords: List[str], max_batch_size: int = 4) -> List[List[str]]:
        """
        Chia danh sách từ khóa thành các cụm nhỏ, luôn kèm theo Anchor Keyword.
        Ví dụ max_batch_size = 4: Mỗi request gửi Anchor + 4 từ khóa = 5 từ khóa tối đa.
        """
        # Loại bỏ anchor nếu đã có trong danh sách từ khóa cần cào
        clean_kws = [k for k in keywords if k.lower().strip() != self.anchor.lower().strip()]
        
        batches = []
        for i in range(0, len(clean_kws), max_batch_size):
            chunk = clean_kws[i:i + max_batch_size]
            batches.append([self.anchor] + chunk)
        
        # Nếu không có từ khóa nào ngoài anchor, batch chỉ có anchor
        if not batches:
            batches.append([self.anchor])
            
        return batches

    def run_category(self, category_key: str, force_refresh: bool = False):
        """Thu thập dữ liệu cho một danh mục từ khóa cụ thể"""
        categories = self.keywords_config.get("categories", {})
        if category_key not in categories:
            raise ValueError(f"Danh mục '{category_key}' không tồn tại trong config. Danh mục hợp lệ: {list(categories.keys())}")

        cat_info = categories[category_key]
        keywords = cat_info.get("keywords", [])
        desc = cat_info.get("description", "")
        self.logger.info(f"=== Bắt đầu thu thập danh mục '{category_key}': {desc} ({len(keywords)} từ khóa) ===")

        batches = self._create_batches(keywords, max_batch_size=4)
        self.logger.info(f"Tổng số batch cần xử lý: {len(batches)}")

        collected_time_dfs = []
        collected_region_dfs = []
        checkpoint = self.lake_manager.load_checkpoint()

        for idx, batch_kws in enumerate(batches, start=1):
            batch_id = f"{category_key}_{self.timeframe_suffix}_batch_{idx}" if self.timeframe_suffix != "5y" else f"{category_key}_batch_{idx}"
            self.logger.info(f"--- Đang xử lý Batch {idx}/{len(batches)} [{self.timeframe_suffix}]: {batch_kws} ---")

            raw_time_parquet = self.lake_manager.raw_dir / "interest_over_time" / f"{batch_id}.parquet"
            raw_reg_parquet = self.lake_manager.raw_dir / "interest_by_region" / f"{batch_id}.parquet"

            # Kiểm tra xem batch này đã được cào trước đó chưa (Resume Checkpoint)
            if not force_refresh and batch_id in checkpoint["completed_batches"] and raw_time_parquet.exists():
                self.logger.info(f"Batch '{batch_id}' đã tồn tại trong Data Lake. Đang nạp từ cache raw...")
                df_time = pd.read_parquet(raw_time_parquet)
                collected_time_dfs.append(df_time)
                if raw_reg_parquet.exists():
                    df_region = pd.read_parquet(raw_reg_parquet)
                    collected_region_dfs.append(df_region)
                continue

            # Gọi Google Trends Client thu thập dữ liệu
            try:
                self.client.build_payload(
                    kw_list=batch_kws,
                    cat=self.cat,
                    timeframe=self.timeframe,
                    geo=self.geo
                )

                # 1. Interest over time
                df_time = self.client.interest_over_time() if self.fetch_over_time else pd.DataFrame()

                # 2. Interest by region (63 tỉnh/thành)
                df_region = self.client.interest_by_region(resolution="SUBREGION") if self.fetch_by_region else pd.DataFrame()

                # 3. Related queries (Chỉ thu thập nếu được bật trong config)
                serializable_rq = {}
                if self.fetch_related:
                    related_queries = self.client.related_queries()
                    for k, v in related_queries.items():
                        serializable_rq[k] = {
                            "top": v["top"].to_dict(orient="records") if v.get("top") is not None else [],
                            "rising": v["rising"].to_dict(orient="records") if v.get("rising") is not None else []
                        }

                # Lưu Raw vào Data Lake
                self.lake_manager.save_raw_batch(
                    batch_id=batch_id,
                    df_time=df_time,
                    df_region=df_region,
                    related_data=serializable_rq
                )

                if df_time is not None and not df_time.empty:
                    collected_time_dfs.append(df_time)
                if df_region is not None and not df_region.empty:
                    collected_region_dfs.append(df_region)

            except Exception as e:
                self.logger.error(f"Lỗi khi thu thập Batch '{batch_id}': {e}")
                # Dừng hoặc tiếp tục tùy lựa chọn; lưu các batch trước đó
                break

        # Chuẩn hóa liên batch (Anchor Normalization)
        if collected_time_dfs:
            self.logger.info(f"Đang thực hiện chuẩn hóa Cross-Batch Normalization bằng Anchor '{self.anchor}'...")
            master_time_df = self.normalizer.normalize_time_series_batches(collected_time_dfs)
            master_region_df = self.normalizer.normalize_region_batches(collected_region_dfs) if collected_region_dfs else None

            master_cat_name = f"{category_key}_{self.timeframe_suffix}" if self.timeframe_suffix != "5y" else category_key

            # Lưu vào Master Zone
            self.lake_manager.save_normalized_master(
                category_name=master_cat_name,
                df_normalized_time=master_time_df,
                df_region=master_region_df
            )

            # Đồng bộ Data Warehouse DuckDB
            if self.enable_duckdb:
                self.lake_manager.sync_to_duckdb(
                    category_name=master_cat_name,
                    df_normalized_time=master_time_df,
                    df_region=master_region_df
                )

            self.logger.info(f"=== Hoàn thành thành công danh mục '{master_cat_name}'! Master shape: {master_time_df.shape} ===")
            return master_time_df
        else:
            self.logger.warning(f"Không có dữ liệu nào được thu thập cho danh mục '{category_key}'.")
            return None

    def run_all(self, force_refresh: bool = False):
        """Chạy toàn bộ các danh mục có trong file cấu hình"""
        categories = list(self.keywords_config.get("categories", {}).keys())
        self.logger.info(f"Bắt đầu thu thập toàn bộ {len(categories)} danh mục: {categories}")
        results = {}
        for cat in categories:
            results[cat] = self.run_category(cat, force_refresh=force_refresh)
        return results

