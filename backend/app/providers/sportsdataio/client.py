"""SportsDataIO NFL v3 HTTP client.

Real, functioning client -- but inert unless SPORTSDATAIO_API_KEY is set, per
the zero-budget requirement. Not exercised in DEMO/LOCAL mode.

Auth: SportsDataIO's API Management gateway accepts the subscription key
either as the `Ocp-Apim-Subscription-Key` header or the `key` query
parameter; this client sends both for maximum compatibility across endpoint
families (scores/stats/odds hosts have occasionally differed in which they
require historically).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import httpx

from app.config import RAW_DIR, settings
from app.core.logging import get_logger

logger = get_logger("providers.sportsdataio")

BASE_URL = "https://api.sportsdata.io/v3/nfl"
CACHE_DIR = RAW_DIR / "sportsdataio_cache"


class SportsDataIONotConfigured(RuntimeError):
    pass


class SportsDataIOClient:
    def __init__(self, api_key: str | None = None, max_retries: int = 3, min_interval_s: float = 0.2):
        self.api_key = api_key if api_key is not None else settings.sportsdataio_api_key
        self.max_retries = max_retries
        self.min_interval_s = min_interval_s
        self._last_call = 0.0
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _cache_path(self, path: str, params: dict) -> Path:
        key = hashlib.sha256(f"{path}?{json.dumps(params, sort_keys=True)}".encode()).hexdigest()
        return CACHE_DIR / f"{key}.json"

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_call = time.monotonic()

    def get(self, path: str, params: dict | None = None, use_cache: bool = True) -> list | dict:
        if not self.is_configured():
            raise SportsDataIONotConfigured(
                "SPORTSDATAIO_API_KEY is not set; SportsDataIO provider is unavailable. "
                "GRIDSTATE falls back to nflverse LOCAL/DEMO data automatically."
            )
        params = dict(params or {})
        cache_file = self._cache_path(path, params)
        if use_cache and cache_file.exists():
            return json.loads(cache_file.read_text())

        url = f"{BASE_URL}{path}"
        params["key"] = self.api_key
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._rate_limit()
            try:
                resp = httpx.get(url, params=params, headers=headers, timeout=30.0)
                if resp.status_code == 429:
                    wait = 2**attempt
                    logger.warning(f"rate limited by SportsDataIO, backing off {wait}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                cache_file.write_text(json.dumps(data))
                return data
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = 2**attempt
                logger.warning(f"SportsDataIO request failed (attempt {attempt}): {exc}, retrying in {wait}s")
                time.sleep(wait)
        raise RuntimeError(f"SportsDataIO request to {path} failed after {self.max_retries} attempts") from last_exc
