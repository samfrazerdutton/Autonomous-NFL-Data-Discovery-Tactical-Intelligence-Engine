"""Build the committed DEMO-mode sample parquet from a downloaded raw nflverse season.

The full nflverse pbp release has ~370 columns (win-probability, EPA
decompositions, tackle assist chains, etc.) that GRIDSTATE's Phase 1-5 slice
does not use. This trims each season to only the columns the ingestion
pipeline actually reads, keeping every real play (no row subsampling), so the
demo dataset stays small in the repo while preserving full statistical power.

Usage: .venv/Scripts/python.exe scripts/build_sample.py 2023 2022
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import polars as pl

from app.config import RAW_DIR, SAMPLE_DIR

RAW_COLUMNS = [
    "game_id",
    "play_id",
    "season",
    "week",
    "season_type",
    "game_date",
    "home_team",
    "away_team",
    "qtr",
    "game_seconds_remaining",
    "score_differential",
    "posteam",
    "defteam",
    "posteam_type",
    "down",
    "ydstogo",
    "yardline_100",
    "goal_to_go",
    "drive",
    "play_type",
    "pass",
    "rush",
    "shotgun",
    "no_huddle",
    "complete_pass",
    "incomplete_pass",
    "interception",
    "fumble_lost",
    "touchdown",
    "first_down",
    "penalty",
    "epa",
    "air_yards",
    "yards_gained",
    "passer_player_id",
    "passer_player_name",
    "rusher_player_id",
    "rusher_player_name",
    "receiver_player_id",
    "receiver_player_name",
    "desc",
]


def build(season: int) -> None:
    src = RAW_DIR / f"pbp_{season}.parquet"
    if not src.exists():
        raise FileNotFoundError(f"expected raw season file at {src}; download it first")
    df = pl.read_parquet(src, columns=RAW_COLUMNS)
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    dest = SAMPLE_DIR / f"pbp_{season}_sample.parquet"
    df.write_parquet(dest, compression="zstd")
    print(f"{season}: {df.height} plays, {src.stat().st_size / 1e6:.1f}MB -> {dest.stat().st_size / 1e6:.1f}MB")


if __name__ == "__main__":
    seasons = [int(s) for s in sys.argv[1:]] or [2023]
    for s in seasons:
        build(s)
