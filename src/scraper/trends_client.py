import time
import random
import logging
from typing import List, Dict, Any, Optional
import urllib3.util.retry

# Patch urllib3 compatibility bug in pytrends when using urllib3 >= 2.0
_orig_retry_init = urllib3.util.retry.Retry.__init__
def _patched_retry_init(self, *args, **kwargs):
    if "method_whitelist" in kwargs:
        kwargs["allowed_methods"] = kwargs.pop("method_whitelist")
    return _orig_retry_init(self, *args, **kwargs)
urllib3.util.retry.Retry.__init__ = _patched_retry_init

from pytrends.request import TrendReq
from pytrends.exceptions import TooManyRequestsError, ResponseError

class RobustTrendsClient:
    """
    Wrapper bảo vệ và tối ưu hóa việc gọi Google Trends API:
    - Tự động khắc phục lỗi method_whitelist của urllib3 2.0+
    - Tự động sleep ngẫu nhiên tránh bot detection
    - Tự động Exponential Backoff khi gặp HTTP 429 Too Many Requests
    """
    def __init__(
        self,
        hl: str = "vi-VN",
        tz: int = 420,
        min_delay: float = 4.0,
        max_delay: float = 8.0,
        max_retries: int = 5,
        backoff_base: float = 20.0,
        logger: Optional[logging.Logger] = None
    ):
        self.hl = hl
        self.tz = tz
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.logger = logger or logging.getLogger("RobustTrendsClient")
        self.last_payload_args = None
        self._init_client()

    def _init_client(self):
        """Khởi tạo session pytrends mới với custom headers"""
        custom_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.pytrends = TrendReq(
            hl=self.hl,
            tz=self.tz,
            requests_args={"headers": custom_headers}
        )
        self.pytrends.headers.update(custom_headers)

    def _random_sleep(self):
        """Nghỉ ngơi ngẫu nhiên giữa các request để mô phỏng hành vi người dùng"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def _execute_with_retry(self, action_name: str, func, *args, **kwargs):
        """Thực thi một hàm với cơ chế Exponential Backoff khi dính rate-limit 429"""
        for attempt in range(self.max_retries):
            try:
                self._random_sleep()
                return func(*args, **kwargs)
            except (TooManyRequestsError, Exception) as e:
                err_msg = str(e)
                is_rate_limit = "429" in err_msg or isinstance(e, TooManyRequestsError) or "response with code 429" in err_msg
                if is_rate_limit and attempt < self.max_retries - 1:
                    sleep_time = self.backoff_base * (2 ** attempt) + random.uniform(2, 6)
                    self.logger.warning(
                        f"[Google 429 Rate Limit] khi gọi '{action_name}'. "
                        f"Đang tạm dừng {sleep_time:.1f}s trước khi thử lại (Lần {attempt+1}/{self.max_retries})..."
                    )
                    time.sleep(sleep_time)
                    # Refresh lại session
                    self._init_client()
                    if self.last_payload_args and action_name != "build_payload":
                        try:
                            self.pytrends.build_payload(**self.last_payload_args)
                        except Exception as pe:
                            self.logger.warning(f"Không thể rebuild payload sau khi reset session: {pe}")
                else:
                    self.logger.error(f"Lỗi khi thực thi '{action_name}': {e}")
                    raise e

    def build_payload(self, kw_list: List[str], cat: int = 0, timeframe: str = "today 5-y", geo: str = "VN"):
        """Gửi request build_payload an toàn"""
        self.last_payload_args = {
            "kw_list": kw_list,
            "cat": cat,
            "timeframe": timeframe,
            "geo": geo
        }
        return self._execute_with_retry(
            f"build_payload({kw_list})",
            lambda: self.pytrends.build_payload(kw_list=kw_list, cat=cat, timeframe=timeframe, geo=geo)
        )

    def interest_over_time(self):
        """Lấy dữ liệu chuỗi thời gian an toàn"""
        return self._execute_with_retry(
            "interest_over_time",
            lambda: self.pytrends.interest_over_time()
        )

    def interest_by_region(self, resolution: str = "SUBREGION"):
        """Lấy dữ liệu mức độ quan tâm theo tỉnh/thành an toàn"""
        return self._execute_with_retry(
            f"interest_by_region({resolution})",
            lambda: self.pytrends.interest_by_region(
                resolution=resolution,
                inc_low_vol=True,
                inc_geo_code=True
            )
        )

    def related_queries(self):
        """Lấy dữ liệu từ khóa liên quan an toàn"""
        try:
            return self._execute_with_retry(
                "related_queries",
                lambda: self.pytrends.related_queries()
            )
        except Exception as e:
            self.logger.warning(f"Không thể lấy related_queries: {e}")
            return {}
