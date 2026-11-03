"""Local Ingestion Backend.
Handles Direct Data loading or running external Fetch Scripts.
"""

import os
import subprocess
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
                        subprocess.run(["python", entry], check=True)
                    else:
                        print(f"[Engine: INGESTION] Bỏ qua script không tìm thấy: {entry}")

        # Trả về các file direct sources làm đầu vào chuẩn
        sources = ingest_cfg.get("direct_sources", {})
        print(f"[Engine: INGESTION] Đã xác thực {len(sources)} nguồn dữ liệu đầu vào.")
        return sources

