"""Example Plugin (Level 2: Class Adapter).
User implements their custom CDF calculation logic here.
No need to know framework internals, just implement `execute(input_uri, output_uri)`.
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np

class CustomUserCDFAdapter:
    """Class Adapter do người dùng tự định nghĩa (Ví dụ dùng Pandas/DuckDB)"""

    def execute(self, input_uri: str, output_uri: str, **kwargs) -> str:
        print(f"[Plugin: CustomUserCDFAdapter] Đang xử lý tùy biến từ: {input_uri}")
        
        # Đọc dữ liệu điểm thi
        df = pd.read_parquet(input_uri)
        
        # Giả lập logic tính toán phân vị riêng của người dùng
        # Ở đây đơn giản là sao lưu/chuẩn hóa và xuất ra output
        Path(output_uri).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_uri, index=False)
        
        print(f"[Plugin: CustomUserCDFAdapter] Đã xuất bảng CDF tùy biến tới: {output_uri}")
        return output_uri

