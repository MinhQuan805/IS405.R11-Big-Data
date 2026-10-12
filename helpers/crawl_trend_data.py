"""
Google Trends Crawler Module using Playwright.

Provides robust, multi-query Google Trends data scraping with:
- Multiple query support (comparison mode up to 5 terms)
- Enums for Google Date Ranges and Geographic Locations
- Multi-tier extraction: Primary (CSV Downloads) -> Fallback (DOM Parsing) -> Network/Offline Fallback
- Retry mechanism with exponential backoff & jitter
- Timeout, CAPTCHA, and HTTP 429 (Rate Limit) detection
- Beautiful, formatted terminal logging
- Strongly typed schema definitions (Dataclasses) with JSON/Dict export

================================================================================
OUTPUT FORMAT SPECIFICATION:
================================================================================

The crawl function returns a `GoogleTrendResult` dataclass object with the
following structure and types:

1. JSON Schema Representation:
--------------------------------------------------------------------------------
{
  "query_terms": ["string", ...],       // List of compared search terms (max 5)
  "date_range": "string",               // Time range token (e.g., "today 12-m", "all")
  "geo": "string",                      // ISO 3166-1 alpha-2 geo code (e.g., "VN", "US")
  "scraped_at": "string",               // ISO 8601 UTC timestamp
  "status": "string",                   // Execution status: "success" | "partial" | "failed"
  "errors": ["string", ...],            // List of encountered errors/warnings (if any)
  "metadata": { ... },                  // Technical metadata (url, attempt, etc.)

  // Widget 1: Interest over time (null if unavailable or snapshot without SVG curve)
  "interest_over_time": {
    "queries": ["string", ...],
    "timeline": [
      {
        "date": "string",               // e.g. "2023-10", "2023-10-15", or "Week 1"
        "values": {
          "<query_term_1>": 85,         // Normalized interest score (0 - 100)
          "<query_term_2>": 40
        }
      }
    ],
    "average_interest": {
      "<query_term_1>": 72.5,          // Average interest over the period
      "<query_term_2>": 35.0
    },
    "data_source": "csv"                // "csv" | "dom" | "offline_dom"
  },

  // Widget 2: Interest by region (subregion / provinces)
  "interest_by_region": {
    "queries": ["string", ...],
    "regions": [
      {
        "region": "string",             // Province / state / country name
        "rank": 1,                      // Rank index (1-based)
        "values": {
          "<query_term_1>": 99,         // Percentage breakdown or normalized score
          "<query_term_2>": 1
        }
      }
    ],
    "data_source": "csv"                // "csv" | "dom" | "offline_dom"
  },

  // Widget 3: Commonly searched queries (Top & Rising)
  "commonly_searched_queries": {
    "top_queries": {
      "<query_term>": [
        {
          "rank": 1,                    // Rank index
          "query": "string",            // Search query text
          "value": 100,                 // Score: 0 - 100 (or "+X%")
          "is_breakout": false,         // True if breakout spike
          "metric_type": "score"        // "score" for Top queries
        }
      ]
    },
    "rising_queries": {
      "<query_term>": [
        {
          "rank": 1,                    // Rank index
          "query": "string",            // Search query text
          "value": "+50%",              // Increase percentage or "Breakout"
          "is_breakout": false,         // True if search interest increased >= 5000%
          "metric_type": "change"       // "change" for Rising queries
        }
      ]
    },
    "data_source": "mixed"              // "csv" | "dom" | "offline_dom"
  }
}

2. Pandas DataFrames Export Format (`result.to_dataframes()`):
--------------------------------------------------------------------------------
- "timeline": DataFrame columns: ['date', '<query_1>', '<query_2>', ...]
- "region": DataFrame columns: ['region', 'rank', '<query_1>', '<query_2>', ...]
- "top_queries": DataFrame columns: ['search_term', 'rank', 'query', 'value']
- "rising_queries": DataFrame columns: ['search_term', 'rank', 'query', 'value', 'is_breakout']
================================================================================
"""

import os
import re
import csv
import io
import sys
import time
import json
import random
import logging
import urllib.parse
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Playwright imports
try:
    from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ==============================================================================
# 1. ENUMS & CONSTANTS
# ==============================================================================

class GoogleDateRange(str, Enum):
    """Common Google Trends time range tokens and custom range constructor."""
    PAST_HOUR = "now 1-H"
    PAST_4_HOURS = "now 4-H"
    PAST_DAY = "now 1-d"
    PAST_7_DAYS = "now 7-d"
    PAST_30_DAYS = "today 1-m"
    PAST_90_DAYS = "today 3-m"
    PAST_12_MONTHS = "today 12-m"
    PAST_5_YEARS = "today 5-y"
    ALL_TIME = "all"  # 2004 to present

    @classmethod
    def custom(cls, start_date: str, end_date: str) -> str:
        """
        Constructs a custom date range string: 'YYYY-MM-DD YYYY-MM-DD'.
        Example: GoogleDateRange.custom("2010-01-01", "2026-10-13") -> "2010-01-01 2026-10-13"
        """
        return f"{start_date.strip()} {end_date.strip()}"


def normalize_date_input(date_val: Union[GoogleDateRange, str]) -> str:
    """
    Normalizes date input supporting:
    - GoogleDateRange Enum (e.g. GoogleDateRange.PAST_12_MONTHS -> 'today 12-m')
    - Custom date ranges (e.g. '2010-01-01 2026-10-13')
    - Pre-encoded URL strings (e.g. '2010-01-01%202026-10-13' -> '2010-01-01 2026-10-13')
    - Plus-separated strings (e.g. '2010-01-01+2026-10-13' -> '2010-01-01 2026-10-13')
    - Relative tokens (e.g. 'now 1-d', 'today 5-y', 'all')
    """
    if isinstance(date_val, GoogleDateRange):
        return date_val.value

    raw = str(date_val).strip()
    # 1. Unquote if already URL-encoded (avoids double encoding '%2520')
    unquoted = urllib.parse.unquote(raw).strip()

    # 2. Convert plus between two YYYY-MM-DD dates into space
    if re.match(r'^\d{4}-\d{2}-\d{2}\+\d{4}-\d{2}-\d{2}$', unquoted):
        unquoted = unquoted.replace('+', ' ')

    # 3. Collapse multiple whitespaces
    unquoted = re.sub(r'\s+', ' ', unquoted)
    return unquoted


class GoogleGeo(str, Enum):
    """Google Trends Geographic Codes (ISO 3166-1 alpha-2)."""
    WORLDWIDE = ""
    VIETNAM = "VN"
    UNITED_STATES = "US"
    UNITED_KINGDOM = "GB"
    JAPAN = "JP"
    SOUTH_KOREA = "KR"
    GERMANY = "DE"
    FRANCE = "FR"
    CANADA = "CA"
    AUSTRALIA = "AU"
    INDIA = "IN"
    SINGAPORE = "SG"

    THAILAND = "TH"
    INDONESIA = "ID"
    MALAYSIA = "MY"
    PHILIPPINES = "PH"
    TAIWAN = "TW"
    BRAZIL = "BR"
    CHINA = "CN"


# User Agents for rotation
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]


# ==============================================================================
# 2. LOGGING CONFIGURATION
# ==============================================================================

def setup_logger(name: str = "GoogleTrendsCrawler", level: int = logging.INFO) -> logging.Logger:
    """Configures a clear, color-coded terminal logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [TrendsCrawler] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

logger = setup_logger()


# ==============================================================================
# 3. SCHEMA DEFINITIONS
# ==============================================================================

@dataclass
class TimelinePoint:
    """Data point in the Interest Over Time series."""
    date: str
    values: Dict[str, Optional[int]] = field(default_factory=dict)


@dataclass
class InterestOverTimeData:
    """Interest Over Time metric schema."""
    queries: List[str]
    timeline: List[TimelinePoint] = field(default_factory=list)
    average_interest: Dict[str, float] = field(default_factory=dict)
    data_source: str = "csv"  # 'csv', 'dom', or 'api'


@dataclass
class RegionInterestItem:
    """Search interest item for a specific subregion or country."""
    region: str
    values: Dict[str, Optional[int]] = field(default_factory=dict)
    rank: Optional[int] = None


@dataclass
class InterestByRegionData:
    """Interest by Region metric schema."""
    queries: List[str]
    regions: List[RegionInterestItem] = field(default_factory=list)
    data_source: str = "csv"  # 'csv', 'dom', or 'api'


@dataclass
class QueryItem:
    """Query item in Commonly Searched Queries (Top / Rising)."""
    rank: int
    query: str
    value: Union[int, str]
    is_breakout: bool = False
    metric_type: str = "score"  # 'score' (0-100) or 'change' (+% / Breakout)


@dataclass
class CommonlySearchedQueriesData:
    """Top and Rising queries grouped by query terms."""
    top_queries: Dict[str, List[QueryItem]] = field(default_factory=dict)
    rising_queries: Dict[str, List[QueryItem]] = field(default_factory=dict)
    data_source: str = "csv"  # 'csv', 'dom', or 'api'


@dataclass
class GoogleTrendResult:
    """Overall result container for Google Trends scraping."""
    query_terms: List[str]
    date_range: str
    geo: str
    interest_over_time: Optional[InterestOverTimeData] = None
    interest_by_region: Optional[InterestByRegionData] = None
    commonly_searched_queries: Optional[CommonlySearchedQueriesData] = None
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "success"  # 'success', 'partial', 'failed'
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts result object to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serializes result object to formatted JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_dataframes(self) -> Dict[str, Any]:
        """
        Exports datasets to pandas DataFrames if pandas is installed.
        Returns dictionary of DataFrames: {'timeline': df, 'region': df, 'top': df, 'rising': df}.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for to_dataframes(). Please run `pip install pandas`.")

        dfs = {}

        # 1. Timeline DataFrame
        if self.interest_over_time and self.interest_over_time.timeline:
            rows = []
            for pt in self.interest_over_time.timeline:
                row = {"date": pt.date}
                row.update(pt.values)
                rows.append(row)
            dfs["timeline"] = pd.DataFrame(rows)

        # 2. Region DataFrame
        if self.interest_by_region and self.interest_by_region.regions:
            rows = []
            for r in self.interest_by_region.regions:
                row = {"region": r.region, "rank": r.rank}
                row.update(r.values)
                rows.append(row)
            dfs["region"] = pd.DataFrame(rows)

        # 3. Top Queries DataFrame
        if self.commonly_searched_queries and self.commonly_searched_queries.top_queries:
            rows = []
            for q_term, q_list in self.commonly_searched_queries.top_queries.items():
                for item in q_list:
                    rows.append({
                        "search_term": q_term,
                        "rank": item.rank,
                        "query": item.query,
                        "value": item.value
                    })
            dfs["top_queries"] = pd.DataFrame(rows)

        # 4. Rising Queries DataFrame
        if self.commonly_searched_queries and self.commonly_searched_queries.rising_queries:
            rows = []
            for q_term, q_list in self.commonly_searched_queries.rising_queries.items():
                for item in q_list:
                    rows.append({
                        "search_term": q_term,
                        "rank": item.rank,
                        "query": item.query,
                        "value": item.value,
                        "is_breakout": item.is_breakout
                    })
            dfs["rising_queries"] = pd.DataFrame(rows)

        return dfs


# ==============================================================================
# 4. DATA PARSERS (CSV & DOM)
# ==============================================================================

class TrendsDataParser:
    """Helper parser for raw CSV streams and DOM tree structures."""

    @staticmethod
    def parse_timeline_csv(csv_text: str, query_terms: List[str]) -> InterestOverTimeData:
        """Parses Google Trends multiTimeline CSV into InterestOverTimeData."""
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        header_idx = -1
        for i, row in enumerate(rows):
            if row and any(h.strip().lower() in ["month", "week", "day", "time"] for h in row):
                header_idx = i
                break

        if header_idx == -1:
            raise ValueError("Timeline CSV header not found.")

        header = rows[header_idx]
        col_names = [c.strip() for c in header[1:]]

        # Map column index to query term
        col_to_term = {}
        for idx, col in enumerate(col_names):
            clean_col = re.sub(r':\s*\(.*?\)', '', col).strip()
            # Match closest query term
            matched = clean_col
            for q in query_terms:
                if q.lower() in clean_col.lower() or clean_col.lower() in q.lower():
                    matched = q
                    break
            col_to_term[idx] = matched

        timeline_points: List[TimelinePoint] = []
        term_sums: Dict[str, int] = {q: 0 for q in query_terms}
        term_counts: Dict[str, int] = {q: 0 for q in query_terms}

        for row in rows[header_idx + 1:]:
            if not row or len(row) < 2:
                continue
            date_str = row[0].strip()
            values: Dict[str, Optional[int]] = {}
            for col_idx, val_str in enumerate(row[1:]):
                term = col_to_term.get(col_idx, f"term_{col_idx}")
                val_clean = val_str.strip()
                if val_clean.startswith("<"):
                    val = 1
                elif val_clean.isdigit():
                    val = int(val_clean)
                else:
                    val = None
                values[term] = val

                if val is not None:
                    term_sums[term] = term_sums.get(term, 0) + val
                    term_counts[term] = term_counts.get(term, 0) + 1

            timeline_points.append(TimelinePoint(date=date_str, values=values))

        averages = {}
        for q in query_terms:
            cnt = term_counts.get(q, 0)
            averages[q] = round(term_sums.get(q, 0) / cnt, 2) if cnt > 0 else 0.0

        return InterestOverTimeData(
            queries=query_terms,
            timeline=timeline_points,
            average_interest=averages,
            data_source="csv"
        )

    @staticmethod
    def parse_region_csv(csv_text: str, query_terms: List[str]) -> InterestByRegionData:
        """Parses Google Trends geoMap CSV into InterestByRegionData."""
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        header_idx = -1
        for i, row in enumerate(rows):
            if row and any(h.strip().lower() in ["region", "subregion", "country", "city"] for h in row):
                header_idx = i
                break

        if header_idx == -1:
            raise ValueError("Region CSV header not found.")

        header = rows[header_idx]
        col_names = [c.strip() for c in header[1:]]

        col_to_term = {}
        for idx, col in enumerate(col_names):
            clean_col = re.sub(r':\s*\(.*?\)', '', col).strip()
            matched = clean_col
            for q in query_terms:
                if q.lower() in clean_col.lower() or clean_col.lower() in q.lower():
                    matched = q
                    break
            col_to_term[idx] = matched

        regions: List[RegionInterestItem] = []
        for rank, row in enumerate(rows[header_idx + 1:], start=1):
            if not row or len(row) < 2:
                continue
            region_name = row[0].strip()
            if not region_name:
                continue

            values: Dict[str, Optional[int]] = {}
            for col_idx, val_str in enumerate(row[1:]):
                term = col_to_term.get(col_idx, f"term_{col_idx}")
                val_clean = val_str.strip().replace("%", "")
                if val_clean.startswith("<"):
                    val = 1
                elif val_clean.isdigit():
                    val = int(val_clean)
                else:
                    val = None
                values[term] = val

            regions.append(RegionInterestItem(
                region=region_name,
                values=values,
                rank=rank
            ))

        return InterestByRegionData(
            queries=query_terms,
            regions=regions,
            data_source="csv"
        )

    @staticmethod
    def parse_queries_csv(csv_text: str, query_term: str, is_rising: bool = False) -> List[QueryItem]:
        """Parses Google Trends relatedQueries CSV into list of QueryItems."""
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        items: List[QueryItem] = []
        start = False
        rank = 1

        for row in rows:
            if not row:
                continue
            first_cell = row[0].strip().upper()
            if first_cell in ["TOP", "RISING", "QUERY"]:
                start = True
                continue
            if not start:
                continue

            query = row[0].strip()
            if not query or query.upper() in ["QUERY", "TOP", "RISING"]:
                continue

            val_raw = row[1].strip() if len(row) > 1 else ""
            is_breakout = "breakout" in val_raw.lower()

            if is_rising:
                items.append(QueryItem(
                    rank=rank,
                    query=query,
                    value=val_raw,
                    is_breakout=is_breakout,
                    metric_type="change"
                ))
            else:
                val: Union[int, str] = int(val_raw) if val_raw.isdigit() else val_raw
                items.append(QueryItem(
                    rank=rank,
                    query=query,
                    value=val,
                    is_breakout=is_breakout,
                    metric_type="score"
                ))
            rank += 1

        return items

    @staticmethod
    def parse_dom_queries_table(page: Any, heading_text: str) -> List[QueryItem]:
        """Fallback: Extracts Top/Rising query items directly from page DOM table."""
        items: List[QueryItem] = []
        try:
            # Locate section container based on h3 heading
            container = page.locator(f'div:has(> div > div > h3:has-text("{heading_text}"))')
            if container.count() == 0:
                container = page.locator(f'div:has(h3:has-text("{heading_text}"))')

            rows = container.locator("table tr").all()
            rank_counter = 1

            for row in rows:
                cells = row.locator("td").all_inner_texts()
                if not cells or len(cells) < 2:
                    continue

                first_val = cells[0].strip()
                if not first_val.isdigit():
                    continue

                rank = int(first_val)
                query_name = cells[1].strip()

                val_text = ""
                for c in cells[2:]:
                    c_clean = c.strip()
                    if c_clean and not any(ign in c_clean for ign in [
                        "more_vert", "query_stats", "Explore", "Add to comparison", "Search it", "More query actions"
                    ]):
                        val_text = c_clean
                        break

                clean_val = re.sub(r'^(north|south|\s*[\u200e\u200f])+', '', val_text).strip()
                is_breakout = "breakout" in clean_val.lower()

                metric = "change" if "rising" in heading_text.lower() else "score"
                val_res: Union[int, str] = int(clean_val) if clean_val.isdigit() else clean_val

                items.append(QueryItem(
                    rank=rank,
                    query=query_name,
                    value=val_res,
                    is_breakout=is_breakout,
                    metric_type=metric
                ))
                rank_counter += 1

        except Exception as e:
            logger.warning(f"DOM fallback parsing error for '{heading_text}': {e}")

        return items

    @staticmethod
    def parse_dom_regions_list(page: Any) -> List[RegionInterestItem]:
        """Fallback: Extracts region search interest from page DOM."""
        items: List[RegionInterestItem] = []
        try:
            # Selector matching Google Trends region cards
            reg_container = page.locator("div.n321jb, div:has(> div > h2:has-text('Interest by region'))")
            if reg_container.count() > 0:
                text_content = reg_container.first.inner_text()
                lines = [l.strip() for l in text_content.split("\n") if l.strip()]

                i = 0
                while i < len(lines):
                    line = lines[i]
                    if line.isdigit() and i + 1 < len(lines):
                        rank = int(line)
                        region_name = lines[i + 1]
                        if not region_name.isdigit() and "of" not in region_name and "Go to" not in region_name:
                            items.append(RegionInterestItem(
                                region=region_name,
                                values={},
                                rank=rank
                            ))
                            i += 2
                            continue
                    i += 1
        except Exception as e:
            logger.warning(f"DOM fallback parsing error for regions: {e}")

        return items


# ==============================================================================
# 5. CORE CRAWLER IMPLEMENTATION
# ==============================================================================

class GoogleTrendsCrawler:
    """
    Playwright-based Google Trends Scraper with anti-detection,
    download interception, DOM fallback, and retry handling.
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 35000,
        max_retries: int = 3,
        retry_delay: float = 3.0,
        proxy: Optional[Dict[str, str]] = None,
        export_dir: Optional[str] = None
    ):
        """
        Initializes the crawler.

        :param headless: Run browser in headless mode (default: True).
        :param timeout: Maximum wait time per action in milliseconds (default: 35000).
        :param max_retries: Number of retries on 429 / timeout (default: 3).
        :param retry_delay: Base delay in seconds for exponential backoff (default: 3.0).
        :param proxy: Optional proxy settings e.g. {'server': 'http://ip:port'}.
        :param export_dir: Optional directory to save raw CSV files.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed! Please run:\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )

        self.headless = headless
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.proxy = proxy
        self.export_dir = export_dir

        if self.export_dir:
            os.makedirs(self.export_dir, exist_ok=True)

    def _build_explore_url(self, queries: List[str], date: str, geo: str) -> str:
        """Constructs Google Trends Explore URL using RFC 3986 percent-encoding (%20 instead of +)."""
        q_param = urllib.parse.quote(",".join(queries), safe='')
        url = f"https://trends.google.com/explore?q={q_param}&hl=en"
        if date:
            clean_date = normalize_date_input(date)
            url += f"&date={urllib.parse.quote(clean_date, safe='')}"
        if geo:
            clean_geo = geo.value if isinstance(geo, GoogleGeo) else str(geo).strip()
            url += f"&geo={urllib.parse.quote(clean_geo, safe='')}"
        return url


    def _setup_browser_context(self, playwright_instance: Any) -> tuple:
        """Launches Chromium with anti-bot evasion arguments."""
        user_agent = random.choice(DEFAULT_USER_AGENTS)
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-background-timer-throttling",
            "--disable-popup-blocking"
        ]

        # Attempt to use system Chrome if installed to evade headless bot detection
        browser = None
        try:
            browser = playwright_instance.chromium.launch(
                channel="chrome",
                headless=self.headless,
                args=args,
                proxy=self.proxy
            )
        except Exception:
            # Fallback to bundled Chromium
            browser = playwright_instance.chromium.launch(
                headless=self.headless,
                args=args,
                proxy=self.proxy
            )

        context = browser.new_context(
            user_agent=user_agent,
            locale="en-US",
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://trends.google.com/"
            }
        )

        # Inject stealth scripts to avoid bot detection
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)

        return browser, context

    def _handle_consent_and_overlays(self, page: Page) -> None:
        """Dismisses Google cookie banner, 'Got it' tips, Gemini prompts, or modals."""
        overlay_selectors = [
            'button[aria-label="Close"]',
            'button[aria-label="close"]',
            'span:has-text("Got it")',
            'button:has-text("Got it")',
            'button:has-text("Accept all")',
            'button:has-text("I agree")',
            'button:has-text("Reject all")'
        ]
        for sel in overlay_selectors:
            try:
                el = page.locator(sel)
                if el.count() > 0 and el.first.is_visible():
                    logger.info(f"Dismissing modal/banner: {sel}")
                    el.first.click(timeout=2000, force=True)
                    page.wait_for_timeout(500)
            except Exception:
                pass



    def _check_rate_limit(self, page: Page) -> bool:
        """Detects Google HTTP 429 Too Many Requests page."""
        title = page.title()
        content = page.content().lower()
        if "429" in title or "too many requests" in title.lower() or "you have sent too many requests" in content:
            return True
        return False

    def _trigger_csv_download(self, page: Page, button_selector: str, timeout: int = 12000) -> Optional[str]:
        """Clicks CSV button and captures downloaded content."""
        btn = page.locator(button_selector)
        if btn.count() == 0:
            return None

        try:
            btn.first.scroll_into_view_if_needed(timeout=3000)
            with page.expect_download(timeout=timeout) as download_info:
                btn.first.click()
            download = download_info.value

            # Save if export_dir specified
            if self.export_dir:
                dest = os.path.join(self.export_dir, download.suggested_filename)
                download.save_as(dest)

            # Read CSV content into string
            temp_path = download.path()
            if temp_path and os.path.exists(temp_path):
                with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()

        except Exception as e:
            logger.debug(f"Download trigger failed for selector '{button_selector}': {e}")

        return None

    def crawl(
        self,
        q: Union[str, List[str]],
        date: Union[GoogleDateRange, str] = GoogleDateRange.PAST_12_MONTHS,
        geo: Union[GoogleGeo, str] = GoogleGeo.VIETNAM,
        offline_html_path: Optional[str] = None
    ) -> GoogleTrendResult:
        """
        Executes Google Trends crawl with retry and fallback mechanisms.

        :param q: Single query string or list of query strings (e.g. ['python', 'java']).
        :param date: Time range token or GoogleDateRange enum (e.g. 'today 12-m').
        :param geo: Country code or GoogleGeo enum (e.g. 'VN', 'US', or '' for worldwide).
        :param offline_html_path: Optional path to an offline HTML snapshot for testing/fallback.
        :return: GoogleTrendResult containing scraped datasets.
        """
        # Normalize inputs
        query_terms = [q.strip()] if isinstance(q, str) else [term.strip() for term in q if term.strip()]
        if not query_terms:
            raise ValueError("Query parameter 'q' must contain at least one non-empty search term.")
        if len(query_terms) > 5:
            logger.warning("Google Trends supports up to 5 comparison terms. Truncating to 5.")
            query_terms = query_terms[:5]

        date_val = normalize_date_input(date)
        geo_val = geo.value if isinstance(geo, GoogleGeo) else str(geo).strip()

        logger.info(f"Initiating Google Trends scrape: queries={query_terms}, date='{date_val}', geo='{geo_val}'")


        # ---------------------------------------------------------
        # Path A: Offline HTML Snapshot extraction (if provided)
        # ---------------------------------------------------------
        if offline_html_path:
            resolved_offline = offline_html_path
            if not os.path.exists(resolved_offline):
                for cand in [
                    os.path.join(os.getcwd(), offline_html_path),
                    os.path.join(os.path.dirname(__file__), "..", offline_html_path)
                ]:
                    if os.path.exists(cand):
                        resolved_offline = cand
                        break
            if os.path.exists(resolved_offline):
                logger.info(f"Reading from offline HTML snapshot: {resolved_offline}")
                return self._crawl_from_offline_file(resolved_offline, query_terms, date_val, geo_val)

        # ---------------------------------------------------------
        # Path B: Live Playwright Crawl with Retry Loop
        # ---------------------------------------------------------
        target_url = self._build_explore_url(query_terms, date_val, geo_val)
        errors: List[str] = []

        for attempt in range(1, self.max_retries + 1):
            logger.info(f"[Attempt {attempt}/{self.max_retries}] Connecting to {target_url}")

            with sync_playwright() as pw:
                browser = None
                try:
                    browser, context = self._setup_browser_context(pw)
                    page = context.new_page()

                    # 1. Navigation
                    try:
                        page.goto(target_url, wait_until="domcontentloaded", timeout=self.timeout)
                    except PlaywrightTimeoutError:
                        logger.warning(f"[Attempt {attempt}] Navigation timed out after {self.timeout}ms")
                        raise

                    self._handle_consent_and_overlays(page)

                    # 2. Check for 429 Rate Limit
                    if self._check_rate_limit(page):
                        msg = f"HTTP 429 Too Many Requests detected on attempt {attempt}"
                        logger.warning(f"[RATE-LIMIT] {msg}")
                        errors.append(msg)
                        raise RuntimeError(msg)

                    # 3. Wait for widget presence
                    logger.info("Waiting for Trends widgets to initialize...")
                    widget_found = False
                    try:
                        page.wait_for_selector(
                            'button[aria-label*="CSV" i], h2:has-text("Interest over time"), h3:has-text("Top queries")',
                            timeout=min(self.timeout, 20000)
                        )
                        widget_found = True
                    except PlaywrightTimeoutError:
                        logger.warning("Explicit widget selector wait timed out; attempting fallback extraction...")

                    # Give scripts a short settling period
                    page.wait_for_timeout(3000)

                    # ---------------------------------------------------------
                    # 4. Extract Data: Widget 1 - Interest Over Time
                    # ---------------------------------------------------------
                    logger.info("Extracting 'Interest over time'...")
                    iot_data = None
                    iot_csv = self._trigger_csv_download(
                        page,
                        'button[aria-label*="interest over time" i][aria-label*="CSV" i], button[aria-label="Download interest over time CSV"]'
                    )
                    if iot_csv:
                        try:
                            iot_data = TrendsDataParser.parse_timeline_csv(iot_csv, query_terms)
                            logger.info(f"✓ Parsed {len(iot_data.timeline)} timeline points via CSV download.")
                        except Exception as e:
                            logger.warning(f"Error parsing timeline CSV: {e}")

                    # ---------------------------------------------------------
                    # 5. Extract Data: Widget 2 - Interest by Region
                    # ---------------------------------------------------------
                    logger.info("Extracting 'Interest by region'...")
                    region_data = None
                    region_csv = self._trigger_csv_download(
                        page,
                        'button[aria-label*="region" i][aria-label*="CSV" i], button[aria-label="Download search interest by region CSV file"]'
                    )
                    if region_csv:
                        try:
                            region_data = TrendsDataParser.parse_region_csv(region_csv, query_terms)
                            logger.info(f"✓ Parsed {len(region_data.regions)} regions via CSV download.")
                        except Exception as e:
                            logger.warning(f"Error parsing region CSV: {e}")

                    if not region_data:
                        logger.info("Region CSV not captured. Trying DOM fallback...")
                        dom_regions = TrendsDataParser.parse_dom_regions_list(page)
                        if dom_regions:
                            region_data = InterestByRegionData(
                                queries=query_terms,
                                regions=dom_regions,
                                data_source="dom"
                            )
                            logger.info(f"✓ Parsed {len(dom_regions)} regions via DOM fallback.")

                    # ---------------------------------------------------------
                    # 6. Extract Data: Widget 3 - Commonly Searched Queries
                    # ---------------------------------------------------------
                    logger.info("Extracting 'Commonly searched queries' (Top & Rising)...")
                    top_queries_dict: Dict[str, List[QueryItem]] = {}
                    rising_queries_dict: Dict[str, List[QueryItem]] = {}

                    # Top Queries
                    top_csv = self._trigger_csv_download(
                        page,
                        'button[aria-label*="top queries" i][aria-label*="CSV" i], button[aria-label="Download top queries CSV"]'
                    )
                    primary_term = query_terms[0]
                    if top_csv:
                        try:
                            top_queries_dict[primary_term] = TrendsDataParser.parse_queries_csv(top_csv, primary_term, is_rising=False)
                            logger.info(f"✓ Parsed {len(top_queries_dict[primary_term])} top queries via CSV.")
                        except Exception as e:
                            logger.warning(f"Error parsing top queries CSV: {e}")

                    if not top_queries_dict.get(primary_term):
                        dom_top = TrendsDataParser.parse_dom_queries_table(page, "Top queries")
                        if dom_top:
                            top_queries_dict[primary_term] = dom_top
                            logger.info(f"✓ Parsed {len(dom_top)} top queries via DOM fallback.")

                    # Rising Queries
                    rising_csv = self._trigger_csv_download(
                        page,
                        'button[aria-label*="rising queries" i][aria-label*="CSV" i], button[aria-label="Download rising queries CSV"]'
                    )
                    if rising_csv:
                        try:
                            rising_queries_dict[primary_term] = TrendsDataParser.parse_queries_csv(rising_csv, primary_term, is_rising=True)
                            logger.info(f"✓ Parsed {len(rising_queries_dict[primary_term])} rising queries via CSV.")
                        except Exception as e:
                            logger.warning(f"Error parsing rising queries CSV: {e}")

                    if not rising_queries_dict.get(primary_term):
                        dom_rising = TrendsDataParser.parse_dom_queries_table(page, "Rising queries")
                        if dom_rising:
                            rising_queries_dict[primary_term] = dom_rising
                            logger.info(f"✓ Parsed {len(dom_rising)} rising queries via DOM fallback.")

                    queries_data = CommonlySearchedQueriesData(
                        top_queries=top_queries_dict,
                        rising_queries=rising_queries_dict,
                        data_source="mixed"
                    )

                    # Determine scrape completeness status
                    has_iot = iot_data is not None and len(iot_data.timeline) > 0
                    has_reg = region_data is not None and len(region_data.regions) > 0
                    has_q = bool(top_queries_dict.get(primary_term) or rising_queries_dict.get(primary_term))

                    if has_iot and has_reg and has_q:
                        final_status = "success"
                    elif has_iot or has_reg or has_q:
                        final_status = "partial"
                    else:
                        final_status = "failed"
                        raise RuntimeError("Live page rendered empty widgets (Google silent throttling or blocked landing state).")

                    logger.info(f"Scrape completed with status: {final_status.upper()}")

                    return GoogleTrendResult(
                        query_terms=query_terms,
                        date_range=date_val,
                        geo=geo_val,
                        interest_over_time=iot_data,
                        interest_by_region=region_data,
                        commonly_searched_queries=queries_data,
                        status=final_status,
                        errors=errors,
                        metadata={
                            "url": target_url,
                            "attempt": attempt,
                            "widgets_detected": widget_found
                        }
                    )


                except Exception as e:
                    err_msg = f"Attempt {attempt} failed: {type(e).__name__} - {str(e)}"
                    logger.error(err_msg)
                    errors.append(err_msg)

                    if attempt < self.max_retries:
                        backoff = (self.retry_delay * (2 ** (attempt - 1))) + random.uniform(0.5, 1.5)
                        logger.info(f"Backing off for {backoff:.2f}s before retry...")
                        time.sleep(backoff)
                finally:
                    if browser:
                        browser.close()

        # If all retries failed, attempt automatic fallback to local snapshot
        logger.error("All live crawl attempts exhausted.")
        local_candidates = [
            "Explore - Google Trends.html",
            os.path.join(os.path.dirname(__file__), "..", "Explore - Google Trends.html"),
            os.path.join(os.getcwd(), "Explore - Google Trends.html")
        ]
        for candidate in local_candidates:
            if os.path.exists(candidate):
                logger.warning(
                    f"[AUTO-FALLBACK] Live scrape was blocked by Google (HTTP 429/Anti-bot). "
                    f"Automatically recovering via local snapshot: '{os.path.normpath(candidate)}'..."
                )
                fallback_res = self._crawl_from_offline_file(candidate, query_terms, date_val, geo_val)
                fallback_res.errors = errors + ["Live scrape was blocked; recovered via local snapshot."]
                return fallback_res

        return GoogleTrendResult(
            query_terms=query_terms,
            date_range=date_val,
            geo=geo_val,
            status="failed",
            errors=errors,
            metadata={"url": target_url}
        )


    def _crawl_from_offline_file(
        self,
        file_path: str,
        query_terms: List[str],
        date: str,
        geo: str
    ) -> GoogleTrendResult:
        """Parses data from a saved Google Trends offline HTML file."""
        from bs4 import BeautifulSoup

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        primary_term = query_terms[0]

        # Top Queries
        top_items = []
        top_q_h = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 'top queries' in tag.get_text().lower())
        if top_q_h:
            container = top_q_h.find_parent('div', class_='fG3KIc') or top_q_h.parent.parent.parent
            table = container.find('table')
            if table:
                for row in table.find_all('tr'):
                    tds = row.find_all('td')
                    if tds and len(tds) >= 2:
                        cells = [td.get_text(' ', strip=True) for td in tds]
                        if cells[0].isdigit():
                            clean_val = re.sub(r'^(north|south|\s*[\u200e\u200f])+', '', cells[3] if len(cells) > 3 else "").strip()
                            top_items.append(QueryItem(
                                rank=int(cells[0]),
                                query=cells[1],
                                value=int(clean_val) if clean_val.isdigit() else clean_val,
                                is_breakout="breakout" in clean_val.lower(),
                                metric_type="score"
                            ))

        # Rising Queries
        rising_items = []
        rising_q_h = soup.find(lambda tag: tag.name in ['h2', 'h3'] and 'rising queries' in tag.get_text().lower())
        if rising_q_h:
            container = rising_q_h.find_parent('div', class_='fG3KIc') or rising_q_h.parent.parent.parent
            table = container.find('table')
            if table:
                for row in table.find_all('tr'):
                    tds = row.find_all('td')
                    if tds and len(tds) >= 2:
                        cells = [td.get_text(' ', strip=True) for td in tds]
                        if cells[0].isdigit():
                            clean_val = re.sub(r'^(north|south|\s*[\u200e\u200f])+', '', cells[3] if len(cells) > 3 else "").strip()
                            rising_items.append(QueryItem(
                                rank=int(cells[0]),
                                query=cells[1],
                                value=clean_val,
                                is_breakout="breakout" in clean_val.lower(),
                                metric_type="change"
                            ))

        # Regions
        regions = []
        n321 = soup.find('div', class_='n321jb')
        if n321:
            lines = [l.strip() for l in n321.get_text('\n').split('\n') if l.strip()]
            i = 0
            while i < len(lines):
                if lines[i].isdigit() and i + 1 < len(lines):
                    rank = int(lines[i])
                    r_name = lines[i + 1]
                    if not r_name.isdigit() and "of" not in r_name and "Go to" not in r_name:
                        regions.append(RegionInterestItem(region=r_name, rank=rank))
                        i += 2
                        continue
                i += 1

        queries_data = CommonlySearchedQueriesData(
            top_queries={primary_term: top_items},
            rising_queries={primary_term: rising_items},
            data_source="offline_dom"
        )
        region_data = InterestByRegionData(
            queries=query_terms,
            regions=regions,
            data_source="offline_dom"
        )

        return GoogleTrendResult(
            query_terms=query_terms,
            date_range=date,
            geo=geo,
            interest_over_time=None,  # Offline HTML does not retain dynamic SVG tick curves
            interest_by_region=region_data,
            commonly_searched_queries=queries_data,
            status="partial",
            metadata={"offline_file": file_path}
        )


# ==============================================================================
# 6. CONVENIENCE FUNCTION
# ==============================================================================

def crawl_trend_data(
    q: Union[str, List[str]],
    date: Union[GoogleDateRange, str] = GoogleDateRange.PAST_12_MONTHS,
    geo: Union[GoogleGeo, str] = GoogleGeo.VIETNAM,
    headless: bool = True,
    timeout: int = 35000,
    max_retries: int = 3,
    retry_delay: float = 3.0,
    export_dir: Optional[str] = None,
    offline_html_path: Optional[str] = None
) -> GoogleTrendResult:
    """
    Main function to crawl Google Trends data.

    :param q: Search query or list of search queries (e.g. ['python', 'golang']).
    :param date: Date range: GoogleDateRange enum, standard token (e.g. 'today 12-m', 'all'),
                 or custom date range: '2010-01-01 2026-10-13', '2010-01-01%202026-10-13',
                 or GoogleDateRange.custom('2010-01-01', '2026-10-13').
    :param geo: Geo code (country string or GoogleGeo enum).
    :param headless: Whether to run Playwright in headless mode (default: True).
    :param timeout: Action timeout in milliseconds (default: 35000).
    :param max_retries: Retry attempts on rate limit or timeouts (default: 3).
    :param retry_delay: Base exponential backoff delay in seconds (default: 3.0).
    :param export_dir: Directory path to persist exported CSV files.
    :param offline_html_path: Local HTML file path for testing or offline extraction.
    :return: GoogleTrendResult schema instance.

    Examples:
    >>> # Example 1: Standard relative token
    >>> res1 = crawl_trend_data(q="python", date=GoogleDateRange.PAST_12_MONTHS, geo="VN")

    >>> # Example 2: Custom date range (YYYY-MM-DD YYYY-MM-DD)
    >>> res2 = crawl_trend_data(q="python", date="2010-01-01 2026-10-13", geo="VN")

    >>> # Example 3: URL-encoded date string
    >>> res3 = crawl_trend_data(q="python", date="2010-01-01%202026-10-13", geo="VN")
    """
    crawler = GoogleTrendsCrawler(
        headless=headless,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
        export_dir=export_dir
    )
    return crawler.crawl(
        q=q,
        date=date,
        geo=geo,
        offline_html_path=offline_html_path
    )


# ==============================================================================
# 7. CLI / STANDALONE TEST EXECUTION
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Google Trends Playwright Crawler")
    parser.add_argument("--q", nargs="+", default=["python"], help="Query terms (up to 5)")
    parser.add_argument(
        "--date",
        default=GoogleDateRange.PAST_12_MONTHS.value,
        help="Date range token (e.g. 'today 12-m', '2010-01-01 2026-10-13', '2010-01-01%%202026-10-13')"
    )
    parser.add_argument("--geo", default=GoogleGeo.VIETNAM.value, help="Geo country code")
    parser.add_argument("--headed", action="store_true", default=False, help="Run with visible browser window")
    parser.add_argument("--offline", default=None, help="Path to offline HTML snapshot")
    parser.add_argument("--out", default=None, help="Output JSON filepath")


    args = parser.parse_args()

    print("\n" + "=" * 60)
    print(" GOOGLE TRENDS PLAYWRIGHT CRAWLER")
    print("=" * 60)

    res = crawl_trend_data(
        q=args.q,
        date=args.date,
        geo=args.geo,
        headless=not args.headed,
        offline_html_path=args.offline
    )


    print("\n" + "=" * 60)
    print(" RESULT SUMMARY:")
    print(f" Status: {res.status.upper()}")
    print(f" Queries: {res.query_terms}")
    print(f" Date: {res.date_range} | Geo: {res.geo}")

    if res.interest_over_time:
        print(f" Timeline Points: {len(res.interest_over_time.timeline)}")
        print(f" Averages: {res.interest_over_time.average_interest}")

    if res.interest_by_region:
        print(f" Regions: {len(res.interest_by_region.regions)}")
        for r in res.interest_by_region.regions[:3]:
            print(f"   - {r.region}: {r.values or r.rank}")

    if res.commonly_searched_queries:
        for q_term in res.query_terms:
            top_list = res.commonly_searched_queries.top_queries.get(q_term, [])
            rising_list = res.commonly_searched_queries.rising_queries.get(q_term, [])
            print(f" Top Queries for '{q_term}': {len(top_list)}")
            for item in top_list[:3]:
                print(f"   - #{item.rank} {item.query}: {item.value}")
            print(f" Rising Queries for '{q_term}': {len(rising_list)}")
            for item in rising_list[:3]:
                print(f"   - #{item.rank} {item.query}: {item.value} (Breakout: {item.is_breakout})")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(res.to_json())
        print(f"\nSaved output to: {args.out}")
    print("=" * 60 + "\n")
