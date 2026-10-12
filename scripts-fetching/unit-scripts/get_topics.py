# Auto-generated script from get_topics.ipynb
# export
import json
import random
import re
import time
from urllib.parse import quote

import pandas as pd
import requests
from pytrends.request import TrendReq

from helpers.get_configs import get_config

MAJORS_PATH = get_config('dirs.yaml', ['cleaned_data', 'majors'], as_path=True)
CUTOFF_SCORES_PATH = get_config('dirs.yaml', ['cleaned_data', 'cutoff_scores'], as_path=True)
SCORE_BLOCKS_PATH = get_config('dirs.yaml', ['cleaned_data', 'score_blocks'], as_path=True)
TOPICS_PATH = get_config('dirs.yaml', ['raw_data', 'trend_topics'], as_path=True)
SCRIPT_OUTPUT_PATH = get_config('dirs.yaml', ['unit_scripts', 'get_topics'], as_path=True)

df_majors = pd.read_csv(MAJORS_PATH, encoding='utf-8', usecols=['major_group_name', 'major_name'])
df_cutoff = pd.read_csv(CUTOFF_SCORES_PATH, encoding='utf-8', usecols=['school_name', 'score_admission_name'])
df_blocks = pd.read_csv(SCORE_BLOCKS_PATH, encoding='utf-8')

# ======================================================================

# export
def unique_values(series, sep=None):
    """Chuẩn hóa khoảng trắng, bỏ rỗng/NaN và loại trùng (không phân biệt hoa/thường), giữ nguyên thứ tự xuất hiện.
    Nếu truyền `sep`, mỗi ô sẽ được tách theo dấu phân cách đó trước khi lấy unique."""
    series = series.dropna().astype(str)
    if sep:
        series = series.str.split(sep).explode()
    cleaned = series.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    seen, result = set(), []
    for value in cleaned:
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


school_names = unique_values(df_cutoff['school_name'])
major_group_names = unique_values(df_majors['major_group_name'])
major_names = unique_values(df_majors['major_name'], sep=';')   # major_name phân cách bằng ';'
admission_method_names = unique_values(df_cutoff['score_admission_name'])

# ======================================================================

# export
SUBJECT_COLUMNS = ['subject1', 'subject2', 'subject3', 'subject4']
SUBJECT_GROUP_COLUMNS = ['subject1', 'subject2', 'subject3', 'subject4']


def build_subject_group_name(row):
    parts = [re.sub(r'\s+', ' ', str(row[c])).strip() for c in SUBJECT_GROUP_COLUMNS if pd.notna(row[c])]
    parts = [p for p in parts if p]
    return ' - '.join(parts)


subject_group_names = unique_values(df_blocks.apply(build_subject_group_name, axis=1))
subject_names = unique_values(df_blocks[SUBJECT_COLUMNS].stack())   # stack() tự bỏ NaN

print(f"school_names:           {len(school_names)}")
print(f"major_group_names:      {len(major_group_names)}")
print(f"major_names:            {len(major_names)}")
print(f"admission_method_names: {len(admission_method_names)}")
print(f"subject_group_names:    {len(subject_group_names)}")
print(f"subject_names:          {len(subject_names)}")

# ======================================================================

# export
# --- Địa điểm / ngôn ngữ: Việt Nam ---
HL = 'vi-VN'
TZ = -420                      # UTC+7, tính theo phút (pytrends dùng giá trị âm cho múi giờ phía Đông)

# --- Timeout / retry ---
REQUEST_TIMEOUT = (5, 15)      # (connect, read) giây
MAX_RETRIES = 3                # số lần thử cho MỖI phương thức (pytrends, thủ công)
BACKOFF_BASE = 2               # chờ = BACKOFF_BASE ** lần_thử + jitter
RATE_LIMIT_MULTIPLIER = 2      # nhân thời gian chờ khi gặp 429
SLEEP_RANGE = (1.0, 2.5)       # nghỉ ngẫu nhiên giữa 2 keyword thành công
CONSECUTIVE_FAIL_LIMIT = 3
COOLDOWN_SECONDS = 60

SUGGESTIONS_URL = 'https://trends.google.com/trends/api/autocomplete/'
OUTPUT_COLUMNS = ['keyword', 'keyword_type', 'mid', 'title', 'type']
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

# ======================================================================

# export
class FetchError(Exception):
    """Mọi phương thức/lần thử đều thất bại cho một keyword."""


def _is_rate_limited(error):
    msg = str(error)
    return '429' in msg or 'Too Many Requests' in msg


class TopicFetcher:
    def __init__(self):
        self.preferred = 'pytrends'   # phương thức vừa thành công gần nhất sẽ được thử trước
        self._reset()

    # ---------- khởi tạo / làm mới session ----------
    def _reset(self):
        try:
            # Lưu ý: không truyền retries/backoff_factor vào TrendReq vì pytrends cũ
            # lỗi với urllib3>=2 (method_whitelist). Tự retry ở bên dưới.
            self.pytrends = TrendReq(hl=HL, tz=TZ, timeout=REQUEST_TIMEOUT)
        except Exception as e:
            print(f"  [warn] Không khởi tạo được TrendReq: {e}")
            self.pytrends = None

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.5',
            'Accept': 'application/json, text/plain, */*',
        })
        try:  # lấy cookie (NID...) giống trình duyệt
            self.session.get('https://trends.google.com/trends/?geo=VN',
                             timeout=REQUEST_TIMEOUT)
        except Exception as e:
            print(f"  [warn] Không lấy được cookie: {e}")

    # ---------- phương thức 1: pytrends ----------
    def _via_pytrends(self, keyword):
        if self.pytrends is None:
            raise RuntimeError('pytrends chưa khởi tạo')
        return self.pytrends.suggestions(keyword=keyword)

    # ---------- phương thức 2: request thủ công ----------
    def _via_manual(self, keyword):
        url = SUGGESTIONS_URL + quote(keyword, safe='')
        resp = self.session.get(url, params={'hl': HL, 'tz': TZ}, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 429:
            raise requests.HTTPError('429 Too Many Requests', response=resp)
        resp.raise_for_status()
        # Google thêm tiền tố chống XSSI ")]}'," trước JSON
        text = re.sub(r"^\)\]\}',?\s*", '', resp.text)
        return json.loads(text)['default']['topics']

    # ---------- điều phối + fallback ----------
    def fetch(self, keyword):
        methods = [('pytrends', self._via_pytrends), ('manual', self._via_manual)]
        methods.sort(key=lambda m: m[0] != self.preferred)   # phương thức ưu tiên lên đầu
        last_error = None
        for method_name, method in methods:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    topics = method(keyword)
                    self.preferred = method_name
                    return [t for t in (topics or []) if isinstance(t, dict)]
                except Exception as e:
                    last_error = e
                    wait = BACKOFF_BASE ** attempt + random.uniform(0, 1)
                    if _is_rate_limited(e):
                        wait *= RATE_LIMIT_MULTIPLIER
                    print(f"  [{method_name}] lần {attempt}/{MAX_RETRIES} lỗi: {e!r} -> chờ {wait:.1f}s")
                    time.sleep(wait)
                    if _is_rate_limited(e):
                        self._reset()          # đổi cookie/session khi bị chặn
            print(f"  [{method_name}] hết lượt thử, chuyển phương thức kế tiếp")
            self._reset()
        raise FetchError(f"{keyword!r}: {last_error!r}")

# ======================================================================

# export
keyword_sources = {
    'school': school_names,
    'major_group': major_group_names,
    'major': major_names,
    'admission_method': admission_method_names,
    'subject_group': subject_group_names,
    'subject': subject_names,
}

tasks = [(ktype, kw) for ktype, kws in keyword_sources.items() for kw in kws]

print(f"Tổng số keyword: {len(tasks)}")
print({k: len(v) for k, v in keyword_sources.items()})

# ======================================================================

# export
rows = []
failed = []
no_result = []
fetcher = TopicFetcher()
consecutive_fails = 0

for i, (ktype, keyword) in enumerate(tasks, start=1):
    try:
        topics = fetcher.fetch(keyword)
        for topic in topics:
            rows.append({
                'keyword': keyword,
                'keyword_type': ktype,
                'mid': topic.get('mid'),
                'title': topic.get('title'),
                'type': topic.get('type'),
            })
        if not topics:
            no_result.append((ktype, keyword))
        consecutive_fails = 0
        print(f"[{i}/{len(tasks)}] ({ktype}) {keyword} -> {len(topics)} topic")
        time.sleep(random.uniform(*SLEEP_RANGE))
    except FetchError as e:
        failed.append((ktype, keyword))
        consecutive_fails += 1
        print(f"[{i}/{len(tasks)}] THẤT BẠI: {e}")
        if consecutive_fails >= CONSECUTIVE_FAIL_LIMIT:
            print(f"  Thất bại liên tiếp {consecutive_fails} lần -> nghỉ {COOLDOWN_SECONDS}s")
            time.sleep(COOLDOWN_SECONDS)
            fetcher._reset()
            consecutive_fails = 0

df_topics = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
df_topics = df_topics.drop_duplicates(subset=['keyword', 'keyword_type', 'mid'])

TOPICS_PATH.parent.mkdir(parents=True, exist_ok=True)
df_topics.to_csv(TOPICS_PATH, index=False, encoding='utf-8')
print(f"Hoàn tất. Số dòng: {len(df_topics)} | Không có topic: {len(no_result)} | Thất bại: {len(failed)}")
if failed:
    print("Keyword thất bại:", failed)
