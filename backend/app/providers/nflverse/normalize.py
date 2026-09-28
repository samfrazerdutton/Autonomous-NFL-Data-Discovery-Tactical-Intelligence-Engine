"""Normalize raw nflverse play-by-play rows into the common Play schema.

Only maps columns verified present in the actual downloaded nflverse parquet
(inspected directly -- see research/football_state.md). Notably, nflverse's
play_by_play release does NOT include offense/defense personnel groupings
(that lives in a separate participation dataset this slice does not ingest),
so `offense_personnel`/`defense_personnel` are left null rather than
fabricated. This is a documented limitation, not an oversight.
"""
from __future__ import annotations

import polars as pl

from app.core.versioning import dataset_version

PLAY_TYPES_WITH_ACTION = {"pass", "run", "punt", "field_goal", "qb_kneel", "qb_spike"}


def normalize_pbp(raw: pl.DataFrame, season: int) -> pl.DataFrame:
    """Return a DataFrame matching app.models.core.Play columns (plus a 'game' frame separately)."""
    df = raw.sort(["game_id", "play_id"])

    df = df.with_columns(
        [
            (pl.col("game_id") + pl.lit("_") + pl.col("play_id").cast(pl.Utf8)).alias("id"),
            pl.col("play_type").shift(1).over(["game_id", "drive"]).alias("prev_play_type"),
            pl.col("play_type").shift(2).over(["game_id", "drive"]).alias("prev_play_type_2"),
            (pl.col("play_id").rank("ordinal").over(["game_id", "drive"])).alias("play_num_in_drive"),
            pl.col("pass").cast(pl.Boolean).alias("pass_play"),
            pl.col("rush").cast(pl.Boolean).alias("rush_play"),
        ]
    )

    bool_cols = [
        "shotgun",
        "no_huddle",
        "complete_pass",
        "incomplete_pass",
        "interception",
        "fumble_lost",
        "touchdown",
        "first_down",
        "penalty",
    ]
    df = df.with_columns([pl.col(c).cast(pl.Boolean) for c in bool_cols])

    dv = dataset_version("nflverse", str(season))

    keep = {
        "id": "id",
        "game_id": "game_id",
        "play_id": "play_id",
        "season": "season",
        "week": "week",
        "season_type": "season_type",
        "qtr": "qtr",
        "game_seconds_remaining": "game_seconds_remaining",
        "score_differential": "score_differential",
        "posteam": "posteam",
        "defteam": "defteam",
        "posteam_type": "posteam_type",
        "down": "down",
        "ydstogo": "ydstogo",
        "yardline_100": "yardline_100",
        "goal_to_go": "goal_to_go",
        "drive": "drive",
        "play_num_in_drive": "play_num_in_drive",
        "prev_play_type": "prev_play_type",
        "prev_play_type_2": "prev_play_type_2",
        "play_type": "play_type",
        "pass_play": "pass_play",
        "rush_play": "rush_play",
        "shotgun": "shotgun",
        "no_huddle": "no_huddle",
        "complete_pass": "complete_pass",
        "incomplete_pass": "incomplete_pass",
        "interception": "interception",
        "fumble_lost": "fumble_lost",
        "touchdown": "touchdown",
        "first_down": "first_down",
        "penalty": "penalty",
        "epa": "epa",
        "air_yards": "air_yards",
        "yards_gained": "yards_gained",
        "passer_player_id": "passer_player_id",
        "passer_player_name": "passer_player_name",
        "rusher_player_id": "rusher_player_id",
        "rusher_player_name": "rusher_player_name",
        "receiver_player_id": "receiver_player_id",
        "receiver_player_name": "receiver_player_name",
        "desc": "desc",
    }
    out = df.select(list(keep.keys())).rename(keep)
    out = out.with_columns(
        [
            pl.lit(None, dtype=pl.Utf8).alias("offense_personnel"),
            pl.lit(None, dtype=pl.Utf8).alias("defense_personnel"),
            pl.lit(dv).alias("dataset_version"),
        ]
    )
    return out


def extract_games(raw: pl.DataFrame, season: int) -> pl.DataFrame:
    dv = dataset_version("nflverse", str(season))
    games = (
        raw.select(["game_id", "season", "week", "game_date", "home_team", "away_team"])
        .unique(subset=["game_id"])
        .with_columns(pl.lit(dv).alias("dataset_version"))
    )
    return games
