# Auto-generated script from score-blocks.ipynb
# export
import re
import pandas as pd
from helpers.get_configs import get_config

RAW_DATA_PATH = get_config('dirs.yaml', ['raw_data', 'score_blocks'], as_path=True)
CLEANED_DATA_PATH = get_config('dirs.yaml', ['cleaned_data', 'score_blocks'], as_path=True)
SCRIPT_OUTPUT_PATH = get_config('dirs.yaml', ['unit_scripts', 'score_blocks'], as_path=True)

# Đọc file CSV vào DataFrame
df = pd.read_csv(RAW_DATA_PATH, encoding='utf-8')

# ======================================================================

# export
import unicodedata

SUBJECT_COLS = ['subject1', 'subject2', 'subject3', 'subject4']

# Ánh xạ áp dụng sau khi đã chuẩn hóa (chữ thường, dấu thanh kiểu mới, lý -> lí)
SUBJECT_MAP = {
    'gdktpl': 'gdkt&pl',
    'hóa': 'hóa học',
    'lí': 'vật lí',
    'địa': 'địa lí',
    'tin': 'tin học',
    'sinh': 'sinh học',
    'văn': 'ngữ văn',
    'năng kiếu báo chí': 'năng khiếu báo chí',  # sửa lỗi gõ sai
}

_NOT_LETTER_AFTER = r'(?![^\W\d_])'  # chỉ đổi dấu thanh khi đứng cuối từ


def _fix_tone(s: str) -> str:
    """Đưa dấu thanh về kiểu mới: hoá -> hóa, khoẻ -> khỏe, thuý -> thúy."""
    tone_o = {'à': 'ò', 'á': 'ó', 'ả': 'ỏ', 'ã': 'õ', 'ạ': 'ọ'}
    tone_e = {'è': 'ò', 'é': 'ó', 'ẻ': 'ỏ', 'ẽ': 'õ', 'ẹ': 'ọ'}
    tone_y = {'ỳ': 'ù', 'ý': 'ú', 'ỷ': 'ủ', 'ỹ': 'ũ', 'ỵ': 'ụ'}
    s = re.sub(r'o([àáảãạ])' + _NOT_LETTER_AFTER, lambda m: tone_o[m.group(1)] + 'a', s)
    s = re.sub(r'o([èéẻẽẹ])' + _NOT_LETTER_AFTER, lambda m: tone_e[m.group(1)] + 'e', s)
    s = re.sub(r'(?<!q)u([ỳýỷỹỵ])' + _NOT_LETTER_AFTER, lambda m: tone_y[m.group(1)] + 'y', s)
    return s


def _normalize_part(part: str) -> str:
    part = part.strip()
    if not part:
        return part
    part = _fix_tone(part)
    part = SUBJECT_MAP.get(part, part)
    # Tên ngôn ngữ viết hoa: tiếng anh -> Tiếng Anh
    part = re.sub(r'\btiếng (\w+)',
                  lambda m: 'Tiếng ' + m.group(1).capitalize(), part)
    return part[0].upper() + part[1:]


def normalize_text(text):
    if pd.isna(text):
        return text

    # 1. Đồng nhất Unicode (tránh các giá trị nhìn giống nhau nhưng khác mã)
    text = unicodedata.normalize('NFC', str(text))

    # 2. Bỏ khoảng trắng đầu/cuối, gộp nhiều khoảng trắng thành 1
    text = re.sub(r'\s+', ' ', text.strip())

    # 3. Về chữ thường toàn bộ
    text = text.lower()

    # 4. Thay "lý" thành "lí"
    text = text.replace('lý', 'lí')

    # 5. Đồng nhất ký tự đặc biệt: "/" và dấu ngoặc
    text = re.sub(r'\s*/\s*', '/', text)     # "a/ b", "a / b" -> "a/b"
    text = re.sub(r'\s*\(\s*', ' (', text)   # "1( kể" -> "1 (kể"
    text = re.sub(r'\s*\)', ')', text)

    # 6. Chuẩn hóa từng môn (tách theo "/"): sửa dấu, ánh xạ, viết hoa
    return '/'.join(_normalize_part(p) for p in text.split('/'))


# Áp dụng cho các cột môn học
for col in SUBJECT_COLS:
    df[col] = df[col].apply(normalize_text)

pd.unique(df[SUBJECT_COLS].values.ravel())

# ======================================================================

# export
CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(CLEANED_DATA_PATH, index=False)
