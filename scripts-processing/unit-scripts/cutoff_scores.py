# Auto-generated script from cutoff-scores.ipynb
# export
import re
import unicodedata
import pandas as pd

from helpers.get_configs import get_config

RAW_DATA_PATH = get_config('dirs.yaml', ['raw_data', 'cutoff_scores'], as_path=True)
CLEANED_DATA_PATH = get_config('dirs.yaml', ['cleaned_data', 'cutoff_scores'], as_path=True)
CLEANED_BLOCKS_PATH = get_config('dirs.yaml', ['cleaned_data', 'score_blocks'], as_path=True)
CLEANED_MAJORS_PATH = get_config('dirs.yaml', ['cleaned_data', 'majors'], as_path=True)
SCRIPT_OUTPUT_PATH = get_config('dirs.yaml', ['unit_scripts', 'cutoff_scores'], as_path=True)

# Đọc file CSV vào DataFrame
df = pd.read_parquet(RAW_DATA_PATH)

# ======================================================================

# export
df.drop(columns=['score_formula', 'score_is_converted_score'], inplace=True)

# ======================================================================

# export
df.dropna(subset=['score_code', 'score_name', 'score_mark', 'score_year', 'score_admission_name', 'province_id', 'province_name'], inplace=True)

# ======================================================================

# export
def remove_newlines(val):
    if pd.isna(val):
        return val
    if isinstance(val, str):
        return re.sub(r'[\r\n]+', ' ', val).strip()
    return val

df = df.map(remove_newlines)

def normalize_score_blocks(val):
    if pd.isna(val) or str(val).strip() == '':
        return val
    s = str(val).replace(',', ';')      # thay dấu ',' thành ';'
    s = re.sub(r'\s+', '', s)           # loại bỏ mọi khoảng trắng (space, tab, \n, ...)
    return s

df['score_blocks'] = df['score_blocks'].apply(normalize_score_blocks)

# ======================================================================

# export
# Ép kiểu score_year về int64
df['score_year'] = df['score_year'].astype('int64')

# Loại bỏ các score_year < 2010 và > 2025
df = df[(df['score_year'] >= 2010) & (df['score_year'] <= 2025)]

# Loại bỏ các score_mark <= 0
df = df[(df['score_year'] > 0)]

# ======================================================================

# export
mapping = {
    '��iểm thi THPT': 'Điểm thi THPT',
    'Điểm xét tốt nghiệp THPT': 'Điểm thi THPT',
    'Đi���m thi THPT': 'Điểm thi THPT',
    'Đi��m thi THPT': 'Điểm thi THPT',

    'Điểm h��c bạ': 'Điểm học bạ',
    'Điểm học b���': 'Điểm học bạ',

    '��iểm ĐGNL HSA': 'Điểm ĐGNL HSA',

    'Đi���m ĐGNL V-ACT': 'Điểm ĐGNL V-ACT',

    'Điểm xét tuyển kết h���p': 'Điểm xét tuyển kết hợp',
    'Điểm xét tuyển kết h��p': 'Điểm xét tuyển kết hợp',
    'Điểm x��t tuyển kết hợp': 'Điểm xét tuyển kết hợp',
    'Điểm xét tuyển k���t hợp': 'Điểm xét tuyển kết hợp',

    'Chứng chỉ qu��c tế': 'Chứng chỉ quốc tế',
    'Chứng chỉ quốc t���': 'Chứng chỉ quốc tế',
    'Chứng chỉ quốc t��': 'Chứng chỉ quốc tế',
}

df['score_admission_name'] = df['score_admission_name'].replace(mapping)

# ======================================================================

# export
df = df.drop_duplicates(
    subset=['school_id', 'score_code', 'score_blocks', 'score_mark', 'score_year', 'score_admission_name'],
    keep='first'
)

# ======================================================================

# export
def normalize_text_unicode(text):
    """Chuẩn hóa text: bỏ dấu, viết thường, để so khớp không phụ thuộc dấu/hoa-thường"""
    if pd.isna(text):
        return ''
    text = str(text).lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.replace('đ', 'd')
    return text

keywords = ['thang 40', 'thang diem 40', 'he so 2', 'nhan 2']

def contains_thang40_keyword(text):
    norm_text = normalize_text_unicode(text)
    return any(kw in norm_text for kw in keywords)

mask_thang40 = df['score_introtext'].apply(contains_thang40_keyword)
df.loc[mask_thang40, 'score_mark'] = (
    df.loc[mask_thang40, 'score_mark'] / 40 * 30
)

# ======================================================================

# export
def remove_iqr_outliers(df, group_col='score_admission_name', value_col='score_mark'):
    """
    Áp dụng phương pháp IQR để loại bỏ ngoại lai trên value_col theo từng nhóm group_col.
    """
    groups = df[group_col].dropna().unique()
    keep_mask = pd.Series(True, index=df.index)

    for group in groups:
        group_idx = df.index[df[group_col] == group]
        subset = df.loc[group_idx, value_col].dropna()

        Q1 = subset.quantile(0.25)
        Q3 = subset.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        subset_filtered = subset[(subset >= lower_bound) & (subset <= upper_bound)]
        outlier_idx = subset.index.difference(subset_filtered.index)
        keep_mask.loc[outlier_idx] = False

    return df.loc[keep_mask].reset_index(drop=True)

df = remove_iqr_outliers(df, group_col='score_admission_name', value_col='score_mark')

# ======================================================================

# export
df_blocks = pd.read_parquet(CLEANED_BLOCKS_PATH)
df_majors = pd.read_parquet(CLEANED_MAJORS_PATH)

valid_block_codes = set(df_blocks['code'].dropna().astype(str).str.strip())

major_score_codes_series = df_majors['score_codes'].dropna().astype(str)
valid_score_codes = set()
for val in major_score_codes_series:
    items = [x.strip() for x in val.split(';') if x.strip() != '']
    valid_score_codes.update(items)

def clean_score_blocks(val):
    if pd.isna(val) or str(val).strip() == '':
        return val
    items = [x.strip() for x in str(val).split(';') if x.strip() != '']
    kept = [x for x in items if x in valid_block_codes]
    return ';'.join(kept) if kept else pd.NA

df['score_blocks'] = df['score_blocks'].apply(clean_score_blocks)

def is_valid_score_code(val):
    if pd.isna(val) or str(val).strip() == '':
        return False
    code = str(val).strip()
    return code in valid_score_codes

mask_valid = df['score_code'].apply(is_valid_score_code)
df = df[mask_valid].reset_index(drop=True)

# ======================================================================

# export
CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(CLEANED_DATA_PATH, index=False)
