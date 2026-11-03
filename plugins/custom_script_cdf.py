"""Example Plugin (Level 1: Zero-Framework-Syntax Standalone Script).
A regular Python script executed as a subprocess black-box.
Zero imports from admission_core!
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="User Independent CDF Calculation Job")
    parser.add_argument("--input", required=True, help="Đường dẫn file đầu vào")
    parser.add_argument("--output", required=True, help="Đường dẫn file kết quả đầu ra")
    args = parser.parse_args()

    print(f"[User Custom Script] Đang đọc dữ liệu từ: {args.input}")
    df = pd.read_parquet(args.input)
    print(f"[User Custom Script] Tổng số dòng: {len(df):,}")

    # Giả lập logic xử lý dữ liệu của người dùng
    out_p = Path(args.output)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output, index=False)
    print(f"[User Custom Script] Hoàn tất và đã lưu tại: {args.output}")

if __name__ == "__main__":
    main()

