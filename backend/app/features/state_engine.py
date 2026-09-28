"""Football State Engine (Section 2 / Phase 2).

Builds the state representation that precedes a play call. Deliberately
excludes play_type, shotgun/no_huddle, and every outcome field (epa,
touchdown, turnovers, ...) from the *state* itself -- those are the ACTION and
OUTCOME that follow a state (Section 9: STATE_t -> ACTION -> OUTCOME ->
STATE_t+1). Downstream modules measure the action/outcome distribution
*conditional on* a state; they never fold it into the state signature, or
"trailing teams pass more" would trivially cluster with "passing" as an input
feature instead of being the finding.

Only fields verified present in the ingested nflverse columns are used (see
providers/nflverse/normalize.py for the source mapping).
"""
from __future__ import annotations

import polars as pl

# Pre-snap STATE features (context only, no action/outcome leakage)
STATE_FEATURE_COLUMNS = [
    "down",
    "ydstogo",
    "yardline_100",
    "score_differential",
    "qtr",
    "game_seconds_remaining",
    "play_num_in_drive",
    "prev_is_pass",
    "prev_is_run",
    "prev2_is_pass",
    "prev2_is_run",
]

# ACTION / OUTCOME fields measured per-state, never used to define a state
OUTCOME_COLUMNS = [
    "pass_play",
    "rush_play",
    "shotgun",
    "no_huddle",
    "complete_pass",
    "touchdown",
    "first_down",
    "interception",
    "fumble_lost",
    "epa",
]


def distance_bucket(ydstogo: float | None) -> str:
    if ydstogo is None:
        return "unknown"
    if ydstogo <= 3:
        return "short_1_3"
    if ydstogo <= 6:
        return "medium_4_6"
    if ydstogo <= 9:
        return "long_7_9"
    return "very_long_10plus"


def field_zone(yardline_100: float | None) -> str:
    if yardline_100 is None:
        return "unknown"
    if yardline_100 < 10:
        return "inside_10"
    if yardline_100 < 20:
        return "red_zone"
    if yardline_100 < 40:
        return "opponent_territory"
    if yardline_100 < 60:
        return "midfield"
    if yardline_100 < 80:
        return "own_territory"
    return "backed_up"


def score_bucket(score_differential: float | None) -> str:
    if score_differential is None:
        return "unknown"
    if score_differential <= -9:
        return "trailing_big"
    if score_differential < 0:
        return "trailing"
    if score_differential == 0:
        return "tied"
    if score_differential < 9:
        return "leading"
    return "leading_big"


def state_key(down: int, dist_b: str, zone: str, score_b: str, qtr: int) -> str:
    return f"d{down}|{dist_b}|{zone}|{score_b}|q{qtr}"


def scrimmage_plays(plays: pl.DataFrame) -> pl.DataFrame:
    """Down-plays universe: excludes kickoffs, extra points, 2pt tries, timeouts, etc."""
    return plays.filter(pl.col("down").is_not_null() & pl.col("down").is_in([1, 2, 3, 4]))


def build_football_states(plays: pl.DataFrame) -> pl.DataFrame:
    """Attach state-key, bucket labels, and lagged-action features to each scrimmage play."""
    df = scrimmage_plays(plays)
    df = df.with_columns(
        [
            pl.col("down").cast(pl.Int64),
            pl.col("qtr").fill_null(1).cast(pl.Int64),
            pl.col("prev_play_type").is_in(["pass"]).cast(pl.Int8).alias("prev_is_pass"),
            pl.col("prev_play_type").is_in(["run"]).cast(pl.Int8).alias("prev_is_run"),
            pl.col("prev_play_type_2").is_in(["pass"]).cast(pl.Int8).alias("prev2_is_pass"),
            pl.col("prev_play_type_2").is_in(["run"]).cast(pl.Int8).alias("prev2_is_run"),
        ]
    )
    df = df.with_columns(
        [
            pl.col("ydstogo").map_elements(distance_bucket, return_dtype=pl.Utf8).alias("distance_bucket"),
            pl.col("yardline_100").map_elements(field_zone, return_dtype=pl.Utf8).alias("field_zone"),
            pl.col("score_differential").map_elements(score_bucket, return_dtype=pl.Utf8).alias("score_bucket"),
        ]
    )
    df = df.with_columns(
        pl.struct(["down", "distance_bucket", "field_zone", "score_bucket", "qtr"])
        .map_elements(
            lambda r: state_key(r["down"], r["distance_bucket"], r["field_zone"], r["score_bucket"], r["qtr"]),
            return_dtype=pl.Utf8,
        )
        .alias("state_key")
    )
    return df


def feature_matrix(states: pl.DataFrame) -> pl.DataFrame:
    """Numeric-only frame ready for standardization + clustering."""
    return states.select(STATE_FEATURE_COLUMNS).fill_null(0)
