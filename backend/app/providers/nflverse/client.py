"""nflverse play-by-play access for LOCAL and DEMO mode.

nflverse (the nflfastR project's data releases) publishes complete, public,
freely redistributable NFL play-by-play parquet files at stable URLs:

    https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_<season>.parquet

DEMO mode reads the trimmed slice committed under backend/data/sample/ (no
network access required). LOCAL mode downloads full seasons on request into
backend/data/raw/ (gitignored) via `download_season`.
"""
from __future__ import annotations

from pathlib import Path

import httpx
import polars as pl

from app.config import RAW_DIR, SAMPLE_DIR
from app.core.logging import get_logger

logger = get_logger("providers.nflverse")

RELEASE_URL_TEMPLATE = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"


def download_season(season: int, dest_dir: Path = RAW_DIR, timeout: float = 300.0) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"pbp_{season}.parquet"
    if dest.exists():
        logger.info(f"season {season} already cached at {dest}")
        return dest
    url = RELEASE_URL_TEMPLATE.format(season=season)
    logger.info(f"downloading {url}")
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1 << 20):
                f.write(chunk)
    return dest


def available_local_seasons() -> list[int]:
    seasons = []
    for p in RAW_DIR.glob("pbp_*.parquet"):
        try:
            seasons.append(int(p.stem.split("_")[1]))
        except (IndexError, ValueError):
            continue
    return sorted(seasons)


def resolve_source(season: int) -> tuple[Path, str]:
    """Return (path, mode) for a season: LOCAL raw cache first, DEMO sample as fallback."""
    local_path = RAW_DIR / f"pbp_{season}.parquet"
    if local_path.exists():
        return local_path, "LOCAL"
    sample_path = SAMPLE_DIR / f"pbp_{season}_sample.parquet"
    if sample_path.exists():
        return sample_path, "DEMO"
    raise FileNotFoundError(
        f"No nflverse data available for season {season} (checked {local_path} and {sample_path}). "
        f"Run ingestion with download=True to fetch it, or use a season with a committed sample."
    )


def load_raw(season: int) -> pl.DataFrame:
    path, _mode = resolve_source(season)
    return pl.read_parquet(path)


def available_sample_seasons() -> list[int]:
    seasons = []
    for p in SAMPLE_DIR.glob("pbp_*_sample.parquet"):
        try:
            seasons.append(int(p.stem.split("_")[1]))
        except (IndexError, ValueError):
            continue
    return sorted(seasons)
