from __future__ import annotations

import polars as pl

from app.features.state_engine import (
    build_football_states,
    distance_bucket,
    field_zone,
    score_bucket,
    scrimmage_plays,
    state_key,
)


def test_distance_bucket_boundaries():
    assert distance_bucket(1) == "short_1_3"
    assert distance_bucket(3) == "short_1_3"
    assert distance_bucket(4) == "medium_4_6"
    assert distance_bucket(7) == "long_7_9"
    assert distance_bucket(10) == "very_long_10plus"
    assert distance_bucket(None) == "unknown"


def test_field_zone_boundaries():
    assert field_zone(5) == "inside_10"
    assert field_zone(15) == "red_zone"
    assert field_zone(35) == "opponent_territory"
    assert field_zone(50) == "midfield"
    assert field_zone(70) == "own_territory"
    assert field_zone(90) == "backed_up"


def test_score_bucket_boundaries():
    assert score_bucket(-10) == "trailing_big"
    assert score_bucket(-3) == "trailing"
    assert score_bucket(0) == "tied"
    assert score_bucket(3) == "leading"
    assert score_bucket(10) == "leading_big"


def test_state_key_is_deterministic_and_human_readable():
    k = state_key(3, "long_7_9", "red_zone", "trailing", 4)
    assert k == "d3|long_7_9|red_zone|trailing|q4"


def test_scrimmage_plays_excludes_null_down():
    df = pl.DataFrame({"down": [1, None, 3, None], "x": [1, 2, 3, 4]})
    out = scrimmage_plays(df)
    assert out.height == 2
    assert out["down"].to_list() == [1, 3]


def test_build_football_states_excludes_action_outcome_columns_from_state_key():
    """The state signature must not encode play_type/epa -- only pre-snap context."""
    df = pl.DataFrame(
        {
            "down": [1, 1],
            "ydstogo": [10, 10],
            "yardline_100": [75, 75],
            "score_differential": [0, 0],
            "qtr": [1, 1],
            "game_seconds_remaining": [3600.0, 3600.0],
            "drive": [1, 2],
            "game_id": ["G1", "G1"],
            "play_id": [1.0, 1.0],
            "play_num_in_drive": [1, 1],
            "prev_play_type": [None, None],
            "prev_play_type_2": [None, None],
            "play_type": ["run", "pass"],  # differs -- but state_key must be identical
            "epa": [0.1, -0.3],
        }
    )
    states = build_football_states(df)
    assert states["state_key"].n_unique() == 1
