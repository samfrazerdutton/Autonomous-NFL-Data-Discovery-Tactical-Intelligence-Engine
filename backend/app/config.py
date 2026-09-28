"""Runtime configuration and mode detection.

GRIDSTATE runs in exactly one of three modes, decided automatically:

- LIVE:  SPORTSDATAIO_API_KEY is set -> SportsDataIO adapter is used for ingestion.
- LOCAL: no key, but a local nflverse data cache/download is used.
- DEMO:  no key, no local cache -> falls back to the committed sample parquet
         under backend/data/sample/. Always clearly labeled as DEMO DATA by the API.
"""
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLE_DIR = DATA_DIR / "sample"


class Mode(str, Enum):
    LIVE = "LIVE"
    LOCAL = "LOCAL"
    DEMO = "DEMO"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR.parent / ".env"), extra="ignore")

    sportsdataio_api_key: str | None = None
    database_url: str = f"sqlite:///{(DATA_DIR / 'gridstate.db').as_posix()}"
    duckdb_path: str = str(DATA_DIR / "analytics.duckdb")
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def mode(self) -> Mode:
        if self.sportsdataio_api_key:
            return Mode.LIVE
        if any(PROCESSED_DIR.glob("*.parquet")) or any(RAW_DIR.glob("*.parquet")):
            return Mode.LOCAL
        return Mode.DEMO


settings = Settings()
