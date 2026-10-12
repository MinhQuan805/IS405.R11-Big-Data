# Auto-generated script from majors.ipynb
# export
import re
import pandas as pd
from helpers.get_configs import get_config

RAW_DATA_PATH = get_config('dirs.yaml', ['raw_data', 'majors'], as_path=True)
CLEANED_DATA_PATH = get_config('dirs.yaml', ['cleaned_data', 'majors'], as_path=True)
SCRIPT_OUTPUT_PATH = get_config('dirs.yaml', ['unit_scripts', 'majors'], as_path=True)

# Đọc file CSV vào DataFrame
df = pd.read_csv(RAW_DATA_PATH, encoding='utf-8')

# ======================================================================

# export
def remove_newlines(val):
    if pd.isna(val):
        return val
    if isinstance(val, str):
        return re.sub(r'[\r\n]+', ' ', val).strip()
    return val

df = df.map(remove_newlines)

def normalize_score_codes(val):
    if pd.isna(val) or str(val).strip() == '':
        return val
    s = str(val).replace(',', ';')
    s = re.sub(r'\s+', '', s)
    return s

df['score_codes'] = df['score_codes'].apply(normalize_score_codes)

# ======================================================================

# export
CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(CLEANED_DATA_PATH, index=False)
