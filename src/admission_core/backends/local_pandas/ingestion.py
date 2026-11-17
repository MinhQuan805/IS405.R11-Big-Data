"""Local Ingestion Backend.
Handles Direct Data loading or running external Fetch Scripts.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any
from admission_core.ports import BaseIngestionPort

class LocalIngestionBackend(BaseIngestionPort):
    """Bộ nạp dữ liệu cục bộ hỗ trợ Direct Injection & Fetch Script"""

    def ingest(self, config: Dict[str, Any]) -> Dict[str, str]:
        print("[Engine: INGESTION] Bắt đầu nạp dữ liệu...")
        ingest_cfg = config.get("data_ingestion", {})
        mode = ingest_cfg.get("mode", "direct_data")

        if mode == "fetch_script":
            scripts = ingest_cfg.get("fetch_scripts", {})
            for name, sc in scripts.items():
                if sc.get("enabled", True):
                    entry = sc.get("entrypoint")
                    if entry and os.path.exists(entry):
                        print(f"[Engine: INGESTION] Đang chạy script fetch: {entry}")
                        subprocess.run([sys.executable, entry], check=True)
                    else:
                        raise FileNotFoundError(f"Không tìm thấy script: {entry}")

        # Trả về các file direct sources làm đầu vào chuẩn
        sources = ingest_cfg.get("direct_sources", {})
        if mode not in {"direct_data", "fetch_script"}:
            raise ValueError(f"Chế độ ingestion không hợp lệ: {mode}")
        for key in ("cutoff_scores", "majors"):
            if not sources.get(key):
                raise ValueError(f"Thiếu nguồn {key}")
        if not any(value for key, value in sources.items() if key.startswith("score_distribution")):
            raise ValueError("Thiếu nguồn phổ điểm")
        for key, uri in sources.items():
            if uri and "://" not in uri and not Path(uri).exists():
                raise FileNotFoundError(f"Nguồn {key} không tồn tại: {uri}")
        print(f"[Engine: INGESTION] Đã xác thực {len(sources)} nguồn dữ liệu đầu vào.")
        return sources

