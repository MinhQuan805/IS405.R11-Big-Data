"""Tiện ích đọc giá trị từ các file YAML trong thư mục config/.

Ví dụ:
    from helpers.get_configs import get_config

    get_config("dirs.yaml", ["cleaned_data", "cutoff_scores"])
    # -> "data-cleaned/admission-cutoff-score/cutoff-scores.csv"

    get_config("dirs.yaml", ["cleaned_data", "cutoff_scores"], as_path=True)
    # -> PosixPath(".../data-cleaned/admission-cutoff-score/cutoff-scores.csv")
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence, Union

import yaml

# File này nằm ở <root>/helpers/get_configs.py -> thư mục gốc là parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"


@lru_cache(maxsize=None)
def _load_yaml(file_name: str) -> Any:
    """Đọc và cache nội dung file YAML (mỗi file chỉ đọc một lần)."""
    file_path = CONFIG_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file config: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_config(
    file_name: str,
    keys: Union[str, Sequence[str], None] = None,
    as_path: bool = False,
) -> Any:
    """Lấy giá trị từ file YAML trong config/.

    Args:
        file_name: Tên file trong config/, ví dụ "dirs.yaml".
        keys: Đường dẫn khóa, ví dụ ["cleaned_data", "cutoff_scores"].
              Có thể truyền chuỗi đơn ("configs") hoặc None để lấy toàn bộ file.
        as_path: True -> trả về Path tuyệt đối (ghép với thư mục gốc dự án).
                 Chỉ dùng khi giá trị là chuỗi đường dẫn.

    Raises:
        FileNotFoundError: file không tồn tại.
        KeyError: khóa không tồn tại hoặc giá trị trung gian không phải dict.
    """
    value = _load_yaml(file_name)

    if keys is None:
        keys = []
    elif isinstance(keys, str):
        keys = [keys]

    for i, key in enumerate(keys):
        if not isinstance(value, dict) or key not in value:
            walked = " -> ".join(keys[: i + 1])
            raise KeyError(f"Không tìm thấy khóa '{walked}' trong {file_name}")
        value = value[key]

    if as_path:
        if not isinstance(value, str):
            raise TypeError(f"Giá trị tại {list(keys)} không phải đường dẫn (chuỗi)")
        return PROJECT_ROOT / value

    return value