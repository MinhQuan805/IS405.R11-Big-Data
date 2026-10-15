"""Xuất các cell có tag `#export` / `# export` từ Jupyter Notebook sang unit script (.py).

Cách dùng trong notebook (xuất chính notebook đang mở):
    from helpers.convert_notebook_2_unit_script import export_to_script
    export_to_script(output_path="scripts-processing/unit-scripts/cutoff_scores.py")

Chỉ định notebook cụ thể:
    export_to_script("scripts-processing/notebooks/majors.ipynb",
                     "scripts-processing/unit-scripts/majors.py")

Dòng lệnh:
    python helpers/convert_notebook_2_unit_script.py <input.ipynb> <output.py>
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Union

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PathLike = Union[str, Path]

# File này nằm ở <root>/helpers/ -> thư mục gốc dự án là parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXPORT_TAGS = ("# export", "#export")
SEPARATOR = "\n\n# " + "=" * 70 + "\n\n"


def _detect_current_notebook() -> Path:
    """Tìm file notebook đang gọi hàm này (thử lần lượt nhiều cách)."""
    # 1. VS Code: tự gán biến __vsc_ipynb_file__ vào namespace của notebook
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is not None:
            vsc_path = ip.user_ns.get("__vsc_ipynb_file__")
            if vsc_path and Path(vsc_path).exists():
                return Path(vsc_path).resolve()
    except ImportError:
        pass

    # 2. Jupyter Server (JupyterLab / Notebook 7): biến môi trường JPY_SESSION_NAME
    session = os.environ.get("JPY_SESSION_NAME")
    if session:
        p = Path(session)
        if p.is_absolute() and p.exists():
            return p.resolve()
        # Đường dẫn tương đối so với thư mục gốc của server -> thử cwd và các thư mục cha
        for base in [Path.cwd(), *Path.cwd().parents]:
            if (base / p).exists():
                return (base / p).resolve()
        if (Path.cwd() / p.name).exists():
            return (Path.cwd() / p.name).resolve()

    # 3. Gói ipynbname (nếu đã cài)
    try:
        import ipynbname  # type: ignore

        return Path(ipynbname.path()).resolve()
    except Exception:
        pass

    # 4. Dự phòng: thư mục hiện tại chỉ có đúng 1 notebook
    candidates = list(Path.cwd().glob("*.ipynb"))
    if len(candidates) == 1:
        return candidates[0].resolve()

    raise RuntimeError(
        "Không tự xác định được notebook hiện tại. "
        "Hãy truyền input_path, ví dụ: export_to_script('path/to/notebook.ipynb', 'out.py')"
    )


def _resolve_input(input_path: Optional[PathLike]) -> Path:
    if input_path is None:
        return _detect_current_notebook()

    p = Path(input_path)
    if p.is_absolute():
        candidates = [p]
    else:
        candidates = [Path.cwd() / p, PROJECT_ROOT / p]

    for cand in candidates:
        if cand.exists():
            return cand.resolve()
    raise FileNotFoundError(f"Không tìm thấy notebook tại {input_path}")


def _resolve_output(output_path: PathLike) -> Path:
    p = Path(output_path)
    # Đường dẫn tương đối được hiểu là so với thư mục gốc dự án (giống dirs.yaml)
    return p if p.is_absolute() else PROJECT_ROOT / p


def _is_export_cell(source: str) -> bool:
    """Cell hợp lệ nếu dòng không rỗng đầu tiên bắt đầu bằng '#export' hoặc '# export'."""
    for line in source.splitlines():
        if line.strip():
            return line.strip().lower().startswith(EXPORT_TAGS)
    return False


def export_to_script(
    input_path: Optional[PathLike] = None,
    output_path: Optional[PathLike] = None,
) -> str:
    """Xuất các cell code có tag #export / # export từ notebook sang file .py.

    Args:
        input_path: Đường dẫn notebook (.ipynb). Bỏ trống -> dùng notebook đang gọi hàm.
        output_path: Đường dẫn file .py đầu ra (bắt buộc). Nếu là đường dẫn tương đối
            thì tính từ thư mục gốc dự án.

    Returns:
        Đường dẫn file .py đã ghi (dạng chuỗi).
    """
    if output_path is None:
        raise ValueError("Thiếu output_path (đường dẫn file .py đầu ra).")

    nb_path = _resolve_input(input_path)
    out_path = _resolve_output(output_path)

    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    code_blocks = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if _is_export_cell(source):
            code_blocks.append(source.strip())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"# Auto-generated script from {nb_path.name}\n" + SEPARATOR.join(code_blocks) + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Đã xuất {len(code_blocks)} cell từ '{nb_path.name}' sang '{out_path}'")
    return str(out_path)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        export_to_script(sys.argv[1], sys.argv[2])
    else:
        print("Cách dùng: python convert_notebook_2_unit_script.py <input.ipynb> <output.py>")
        sys.exit(1)