import sys
import argparse
from pathlib import Path

# Đảm bảo mã hóa UTF-8 cho console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.scraper.google_trends_scraper import GoogleTrendsPipeline

def main():
    parser = argparse.ArgumentParser(
        description="Google Trends Scraper & Ingestion Pipeline"
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Danh mục từ khóa cần cào (ví dụ: majors_it, universities_it, admission_signals, job_market_signals)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Cào toàn bộ tất cả danh mục được cấu hình"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bỏ qua checkpoint, cào lại từ đầu và ghi đè"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default=None,
        help="Khung thời gian cào: '1y' (1 năm qua), '3m' (3 tháng qua), '5y' (5 năm qua, mặc định)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/scraper_config.yaml",
        help="Đường dẫn file cấu hình scraper"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default="config/keywords_it.yaml",
        help="Đường dẫn file danh mục từ khóa"
    )

    args = parser.parse_args()

    pipeline = GoogleTrendsPipeline(
        config_path=args.config,
        keywords_path=args.keywords,
        timeframe=args.timeframe
    )

    if args.all:
        pipeline.run_all(force_refresh=args.force)
    elif args.category:
        pipeline.run_category(args.category, force_refresh=args.force)
    else:
        # Mặc định: cào danh mục ngành CNTT trọng điểm (Giai đoạn 1)
        print("Chưa chỉ định danh mục. Mặc định sẽ cào danh mục 'majors_it'. Dùng --all để cào tất cả.")
        pipeline.run_category("majors_it", force_refresh=args.force)

if __name__ == "__main__":
    main()

