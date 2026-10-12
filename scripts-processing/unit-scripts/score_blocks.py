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
def normalize_text(text):
    if pd.isna(text):
        return text
    
    # 1. Loại bỏ khoảng trắng đầu/cuối
    text = text.strip()
    
    # 2. Loại bỏ 2 dấu cách liên tiếp trở lên -> thành 1 dấu cách
    text = re.sub(r'\s+', ' ', text)
    
    # 3. Đưa về chữ thường toàn bộ trước
    text = text.lower()
    
    # 4. Thay thế "lý" thành "lí"
    text = text.replace('lý', 'lí')
    
    # 5. In hoa chữ cái đầu tiên, còn lại giữ nguyên (chữ thường)
    if text:
        text = text[0].upper() + text[1:]
    
    return text

# Áp dụng cho 3 cột môn học
for col in ['subject1', 'subject2', 'subject3']:
    df[col] = df[col].apply(normalize_text)

# ======================================================================

# export
CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(CLEANED_DATA_PATH, index=False)
