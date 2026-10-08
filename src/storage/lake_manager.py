import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import duckdb

class DataLakeManager:
    """
    Quản lý lưu trữ Data Lake và nạp vào Data Warehouse DuckDB:
    - Data Lake Raw: data/lake/raw/ (Parquet / CSV / JSON)
    - Data Lake Normalized: data/lake/normalized/
    - Data Warehouse: data/warehouse/trends.duckdb
    - Quản lý Checkpoints tránh cào trùng lặp dữ liệu
    """
    def __init__(
        self,
        raw_dir: str = "data/lake/raw",
        normalized_dir: str = "data/lake/normalized",
        duckdb_path: str = "data/warehouse/trends.duckdb",
        logger: Optional[logging.Logger] = None
    ):
        self.raw_dir = Path(raw_dir)
        self.normalized_dir = Path(normalized_dir)
        self.duckdb_path = Path(duckdb_path)
        self.logger = logger or logging.getLogger("DataLakeManager")

        self._init_directories()
        self.checkpoint_file = self.raw_dir / "checkpoints" / "scrape_checkpoint.json"

    def _init_directories(self):
        """Khởi tạo cấu trúc thư mục Data Lake"""
        (self.raw_dir / "interest_over_time").mkdir(parents=True, exist_ok=True)
        (self.raw_dir / "interest_by_region").mkdir(parents=True, exist_ok=True)
        (self.raw_dir / "related_queries").mkdir(parents=True, exist_ok=True)
        (self.raw_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        self.normalized_dir.mkdir(parents=True, exist_ok=True)
        self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)

    def load_checkpoint(self) -> Dict[str, Any]:
        """Đọc trạng thái checkpoint hiện tại"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Không thể đọc checkpoint: {e}. Tạo mới.")
        return {"completed_batches": [], "last_updated": None}

    def save_checkpoint(self, batch_id: str):
        """Cập nhật checkpoint sau khi hoàn thành một batch"""
        cp = self.load_checkpoint()
        if batch_id not in cp["completed_batches"]:
            cp["completed_batches"].append(batch_id)
        cp["last_updated"] = datetime.now().isoformat()
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(cp, f, ensure_ascii=False, indent=2)

    def save_raw_batch(
        self,
        batch_id: str,
        df_time: Optional[pd.DataFrame] = None,
        df_region: Optional[pd.DataFrame] = None,
        related_data: Optional[Dict[str, Any]] = None
    ):
        """Lưu dữ liệu raw theo từng batch vào Data Lake (cả Parquet và CSV)"""
        # 1. Interest Over Time
        if df_time is not None and not df_time.empty:
            parquet_path = self.raw_dir / "interest_over_time" / f"{batch_id}.parquet"
            csv_path = self.raw_dir / "interest_over_time" / f"{batch_id}.csv"
            
            df_time.to_parquet(parquet_path, engine="pyarrow", index=True)
            df_time.to_csv(csv_path, encoding="utf-8-sig", index=True)
            self.logger.info(f"Đã lưu Raw Time Series: {parquet_path.name}")

        # 2. Interest By Region
        if df_region is not None and not df_region.empty:
            parquet_path = self.raw_dir / "interest_by_region" / f"{batch_id}.parquet"
            csv_path = self.raw_dir / "interest_by_region" / f"{batch_id}.csv"
            
            df_region.to_parquet(parquet_path, engine="pyarrow", index=True)
            df_region.to_csv(csv_path, encoding="utf-8-sig", index=True)
            self.logger.info(f"Đã lưu Raw Region: {parquet_path.name}")

        # 3. Related queries
        if related_data:
            json_path = self.raw_dir / "related_queries" / f"{batch_id}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(related_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Đã lưu Raw Related Queries: {json_path.name}")

        self.save_checkpoint(batch_id)

    def save_normalized_master(
        self,
        category_name: str,
        df_normalized_time: pd.DataFrame,
        df_region: Optional[pd.DataFrame] = None
    ):
        """Lưu bảng tổng hợp master sau khi đã chuẩn hóa cross-keyword"""
        # Time series normalized
        ts_parquet = self.normalized_dir / f"master_trends_{category_name}.parquet"
        ts_csv = self.normalized_dir / f"master_trends_{category_name}.csv"
        
        df_normalized_time.to_parquet(ts_parquet, engine="pyarrow", index=True)
        df_normalized_time.to_csv(ts_csv, encoding="utf-8-sig", index=True)
        self.logger.info(f"Đã lưu Master Normalized Time Series: {ts_parquet.name}")

        # Region master
        if df_region is not None and not df_region.empty:
            reg_parquet = self.normalized_dir / f"master_region_{category_name}.parquet"
            reg_csv = self.normalized_dir / f"master_region_{category_name}.csv"
            df_region.to_parquet(reg_parquet, engine="pyarrow", index=True)
            df_region.to_csv(reg_csv, encoding="utf-8-sig", index=True)
            self.logger.info(f"Đã lưu Master Region: {reg_parquet.name}")

    def sync_to_duckdb(self, category_name: str, df_normalized_time: pd.DataFrame, df_region: Optional[pd.DataFrame] = None):
        """
        Nạp dữ liệu trực tiếp vào Data Warehouse DuckDB
        phục vụ truy vấn phân tích SQL và kết nối với PySpark / Feature Engineering
        """
        import time
        max_attempts = 3
        con = None
        for attempt in range(max_attempts):
            try:
                con = duckdb.connect(str(self.duckdb_path))
                break
            except Exception as e:
                if "used by another process" in str(e) and attempt < max_attempts - 1:
                    self.logger.warning(f"File DuckDB đang bận (lần {attempt+1}/{max_attempts}). Đang chờ 2s trước khi thử lại...")
                    time.sleep(2)
                else:
                    self.logger.warning(
                        f"Không thể mở DuckDB để ghi: {e}. "
                        "Gợi ý: Hãy đóng các tab đang xem DuckDB trong VS Code hoặc DBeaver. "
                        "Dữ liệu vẫn được lưu an toàn tuyệt đối trong Data Lake Parquet/CSV."
                    )
                    return

        try:
            # Reset index để đưa cột date thành column
            df_time_sql = df_normalized_time.reset_index()
            # Đổi tên cột date nếu là index
            if "date" not in df_time_sql.columns and "index" in df_time_sql.columns:
                df_time_sql = df_time_sql.rename(columns={"index": "date"})

            table_time_name = f"trends_time_{category_name}"
            con.register("df_time_view", df_time_sql)
            con.execute(f"CREATE OR REPLACE TABLE {table_time_name} AS SELECT * FROM df_time_view")
            self.logger.info(f"DuckDB: Đã cập nhật bảng '{table_time_name}' ({len(df_time_sql)} dòng)")

            if df_region is not None and not df_region.empty:
                df_reg_sql = df_region.reset_index()
                table_reg_name = f"trends_region_{category_name}"
                con.register("df_reg_view", df_reg_sql)
                con.execute(f"CREATE OR REPLACE TABLE {table_reg_name} AS SELECT * FROM df_reg_view")
                self.logger.info(f"DuckDB: Đã cập nhật bảng '{table_reg_name}' ({len(df_reg_sql)} dòng)")

            # Ghi nhật ký metadata vào bảng sys_trends_sync_log
            con.execute("""
                CREATE TABLE IF NOT EXISTS sys_trends_sync_log (
                    category VARCHAR,
                    sync_time TIMESTAMP,
                    num_records INTEGER,
                    columns_count INTEGER
                )
            """)
            con.execute(f"""
                INSERT INTO sys_trends_sync_log VALUES (
                    '{category_name}', 
                    CURRENT_TIMESTAMP, 
                    {len(df_time_sql)}, 
                    {len(df_time_sql.columns)}
                )
            """)
            con.close()
            self.logger.info(f"Hoàn tất đồng bộ Data Warehouse DuckDB tại: {self.duckdb_path}")
        except Exception as e:
            self.logger.error(f"Lỗi khi đồng bộ DuckDB: {e}")
            if con:
                try: con.close()
                except: pass

