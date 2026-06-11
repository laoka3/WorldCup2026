"""
Base classes for optional, compliant web scraping adapters.

Scraping is disabled unless ENABLE_WEB_SCRAPING=true.
Adapters must not bypass login, CAPTCHA, Cloudflare, paywalls, robots rules, or
anti-bot protections. Raw results must be cached before transformation.
"""

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_CACHE_DIR = os.path.join(BASE_DIR, "data", "cache", "raw_scrapers")


@dataclass
class ScraperMetadata:
    source_name: str
    source_url: str
    allowed_by_robots_check: str
    rate_limit_seconds: int
    fetched_at: str
    warning: str = ""


class ScraperDisabledError(RuntimeError):
    pass


class BaseScraper:
    source_name = "base"
    source_url = ""
    allowed_by_robots_check = "unknown"
    rate_limit_seconds = 30

    def __init__(self):
        if os.getenv("ENABLE_WEB_SCRAPING", "").lower() != "true":
            raise ScraperDisabledError("Web scraping is disabled. Set ENABLE_WEB_SCRAPING=true to run an adapter.")
        if self.rate_limit_seconds < 10:
            raise ValueError("rate_limit_seconds must be at least 10 seconds.")

    def metadata(self, warning=""):
        return ScraperMetadata(
            source_name=self.source_name,
            source_url=self.source_url,
            allowed_by_robots_check=self.allowed_by_robots_check,
            rate_limit_seconds=self.rate_limit_seconds,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            warning=warning,
        )

    def sleep_for_rate_limit(self):
        time.sleep(self.rate_limit_seconds)

    def fetch_raw(self):
        raise NotImplementedError("Concrete scrapers must implement fetch_raw().")

    def parse_raw(self, raw):
        raise NotImplementedError("Concrete scrapers must implement parse_raw().")

    def write_raw_cache(self, name, raw, warning=""):
        os.makedirs(RAW_CACHE_DIR, exist_ok=True)
        path = os.path.join(RAW_CACHE_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"meta": asdict(self.metadata(warning)), "raw": raw}, f, ensure_ascii=False, indent=2)
        return path
