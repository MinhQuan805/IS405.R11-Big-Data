"""Chuyển đổi file hoặc thư mục chứa file CSV sang định dạng Parquet.

Cách dùng trong Python:
    from helpers.convert_to_parquet import convert_to_parquet

    # Chuyển đổi 1 file CSV (giữ lại file csv gốc):
    convert_to_parquet("data-cleaned/admission-cutoff-score/score-blocks.csv")

    # Chuyển đổi toàn bộ CSV trong thư mục (xóa file csv gốc sau khi chuyển đổi):
    convert_to_parquet("data-cleaned", inplace=True)

    # Chuyển đổi toàn bộ project:
    convert_to_parquet(".", inplace=False)

Dòng lệnh (Terminal):
    python helpers/convert_to_parquet.py <path> [--inplace] [--compression snappy]
    # Ví dụ:
    python helpers/convert_to_parquet.py data-raw
    python helpers/convert_to_parquet.py data-cleaned/admission-cutoff-score/majors.csv --inplace
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Set, Union

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PathLike = Union[str, Path]

# Thư mục gốc dự án (file này nằm ở <root>/helpers/ -> parents[1])
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Các thư mục hệ thống hoặc môi trường cần bỏ qua khi quét thư mục
IGNORED_DIRS: Set[str] = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    ".vscode",
    ".idea",
    ".pytest_cache",
    ".tours",
}


def _resolve_target_path(path: PathLike) -> Path:
    """Xác định đường dẫn tuyệt đối của file hoặc thư mục đích."""
    p = Path(path)
    if p.is_absolute():
        if p.exists():
            return p.resolve()
        raise FileNotFoundError(f"Không tìm thấy đường dẫn: {p}")

    candidates = [Path.cwd() / p, PROJECT_ROOT / p]
    for cand in candidates:
        if cand.exists():
            return cand.resolve()

    raise FileNotFoundError(f"Không tìm thấy đường dẫn: '{path}' (đã tìm tại cwd và project root)")


def _is_ignored(path: Path) -> bool:
    """Kiểm tra đường dẫn có chứa thư mục cần bỏ qua không."""
    return any(part in IGNORED_DIRS for part in path.parts)


def _format_size(size_bytes: int) -> str:
    """Format dung lượng dạng dễ đọc (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _convert_single_csv(
    csv_path: Path,
    output_path: Optional[Path] = None,
    inplace: bool = False,
    compression: str = "snappy",
) -> Path:
    """Chuyển đổi một file CSV sang Parquet.

    Args:
        csv_path: Đường dẫn file CSV.
        output_path: Đường dẫn file Parquet đích (mặc định cùng tên, đổi đuôi .parquet).
        inplace: Nếu True, xóa file CSV gốc sau khi chuyển đổi thành công.
        compression: Chuẩn nén Parquet ('snappy', 'gzip', 'zstd', 'none').

    Returns:
        Đường dẫn file Parquet đã tạo.
    """
    if output_path is None:
        output_path = csv_path.with_suffix(".parquet")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    orig_size = csv_path.stat().st_size

    # Ưu tiên sử dụng PyArrow vì hiệu năng vượt trội với file lớn
    num_rows = 0
    num_cols = 0
    converted_ok = False

    try:
        import pyarrow.csv as pv
        import pyarrow.parquet as pq

        table = pv.read_csv(csv_path)
        num_rows = table.num_rows
        num_cols = table.num_columns
        pq.write_table(
            table,
            output_path,
            compression=None if compression.lower() == "none" else compression,
        )
        converted_ok = True
    except Exception as pa_err:
        # Fallback sang pandas nếu pyarrow.csv gặp lỗi định dạng đặc biệt
        try:
            import pandas as pd

            df = pd.read_csv(csv_path, low_memory=False, encoding="utf-8")
            num_rows, num_cols = df.shape
            df.to_parquet(
                output_path,
                index=False,
                engine="pyarrow",
                compression=None if compression.lower() == "none" else compression,
            )
            converted_ok = True
        except UnicodeDecodeError:
            import pandas as pd

            df = pd.read_csv(csv_path, low_memory=False, encoding="latin1")
            num_rows, num_cols = df.shape
            df.to_parquet(
                output_path,
                index=False,
                engine="pyarrow",
                compression=None if compression.lower() == "none" else compression,
            )
            converted_ok = True
        except Exception as pd_err:
            raise RuntimeError(
                f"Lỗi khi chuyển đổi '{csv_path.name}':\n"
                f"- PyArrow error: {pa_err}\n"
                f"- Pandas error: {pd_err}"
            ) from pd_err

    if not converted_ok or not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Ghi file parquet thất bại hoặc file rỗng: {output_path}")

    elapsed = time.time() - start_time
    new_size = output_path.stat().st_size
    reduction = (1 - (new_size / orig_size)) * 100 if orig_size > 0 else 0

    try:
        rel_src = csv_path.relative_to(PROJECT_ROOT)
        rel_dst = output_path.relative_to(PROJECT_ROOT)
    except ValueError:
        rel_src = csv_path
        rel_dst = output_path

    print(
        f"[✓] {rel_src} -> {rel_dst.name} | "
        f"{num_rows:,} dòng, {num_cols} cột | "
        f"{_format_size(orig_size)} -> {_format_size(new_size)} (-{reduction:.1f}%) | "
        f"{elapsed:.2f}s"
    )

    if inplace:
        try:
            csv_path.unlink()
            print(f"    (-) Đã xóa file CSV gốc (inplace=True): {rel_src}")
        except Exception as e:
            print(f"    (!) Cảnh báo: Không thể xóa file gốc {rel_src}: {e}", file=sys.stderr)

    return output_path


def convert_to_parquet(
    path: PathLike,
    inplace: bool = False,
    recursive: bool = True,
    compression: str = "snappy",
) -> List[Path]:
    """Chuyển đổi một file CSV hoặc các file CSV trong thư mục sang Parquet.

    Args:
        path: Đường dẫn file CSV hoặc thư mục chứa các file CSV.
        inplace: Nếu True, xóa file CSV gốc sau khi chuyển đổi thành công.
                 Nếu False (mặc định), giữ nguyên file CSV gốc.
        recursive: Nếu True (mặc định), duyệt đệ quy các thư mục con (bỏ qua .venv, .git,...).
        compression: Thuật toán nén Parquet ('snappy', 'gzip', 'zstd', 'none'). Mặc định 'snappy'.

    Returns:
        Danh sách các đường dẫn Path của file Parquet đã tạo.
    """
    target = _resolve_target_path(path)

    if target.is_file():
        if target.suffix.lower() != ".csv":
            raise ValueError(f"Đường dẫn file '{target}' không phải file CSV (.csv).")
        return [_convert_single_csv(target, inplace=inplace, compression=compression)]

    if target.is_dir():
        pattern = "**/*.csv" if recursive else "*.csv"
        csv_files = [p for p in target.glob(pattern) if p.is_file() and not _is_ignored(p)]

        if not csv_files:
            print(f"Không tìm thấy file CSV nào trong '{target}' (đã bỏ qua các thư mục ẩn/.venv).")
            return []

        print(f"Tìm thấy {len(csv_files)} file CSV cần chuyển đổi trong '{target}'. Bắt đầu xử lý...")
        total_start = time.time()
        results: List[Path] = []

        for csv_file in sorted(csv_files):
            try:
                parquet_path = _convert_single_csv(
                    csv_file,
                    inplace=inplace,
                    compression=compression,
                )
                results.append(parquet_path)
            except Exception as e:
                print(f"[✗] Lỗi khi xử lý file '{csv_file}': {e}", file=sys.stderr)

        total_elapsed = time.time() - total_start
        print(
            f"--> Hoàn thành! Đã chuyển đổi {len(results)}/{len(csv_files)} file CSV sang Parquet "
            f"trong {total_elapsed:.2f}s."
        )
        return results

    raise FileNotFoundError(f"Đường dẫn không hợp lệ: {target}")


def main() -> None:
    """Hàm chạy từ terminal."""
    parser = argparse.ArgumentParser(
        description="Chuyển đổi file CSV hoặc thư mục chứa CSV sang định dạng Parquet.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "path",
        help="Đường dẫn tới file .csv hoặc thư mục chứa các file .csv cần chuyển.",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Xóa file CSV gốc sau khi đã chuyển đổi thành công sang Parquet.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Không quét đệ quy các thư mục con khi truyền vào thư mục.",
    )
    parser.add_argument(
        "--compression",
        default="snappy",
        choices=["snappy", "gzip", "zstd", "none"],
        help="Thuật toán nén của Parquet.",
    )

    args = parser.parse_args()

    try:
        convert_to_parquet(
            path=args.path,
            inplace=args.inplace,
            recursive=not args.no_recursive,
            compression=args.compression,
        )
    except Exception as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

