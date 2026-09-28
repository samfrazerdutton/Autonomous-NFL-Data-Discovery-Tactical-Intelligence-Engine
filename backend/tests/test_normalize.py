from __future__ import annotations

import polars as pl

from app.providers.nflverse.normalize import extract_games, normalize_pbp

RAW_COLUMNS = [
    "game_id", "play_id", "season", "week", "season_type", "game_date", "home_team", "away_team",
    "qtr", "game_seconds_remaining", "score_differential", "posteam", "defteam", "posteam_type",
    "down", "ydstogo", "yardline_100", "goal_to_go", "drive", "play_type", "pass", "rush",
    "shotgun", "no_huddle", "complete_pass", "incomplete_pass", "interception", "fumble_lost",
    "touchdown", "first_down", "penalty", "epa", "air_yards", "yards_gained",
    "passer_player_id", "passer_player_name", "rusher_player_id", "rusher_player_name",
    "receiver_player_id", "receiver_player_name", "desc",
]


def _row(**overrides) -> dict:
    base = {c: None for c in RAW_COLUMNS}
    base.update(
        season=2023, season_type="REG", week=1, home_team="AAA", away_team="BBB",
        game_date="2023-09-10", posteam_type="home", goal_to_go=0, shotgun=False,
        no_huddle=False, complete_pass=False, incomplete_pass=False, interception=False,
        fumble_lost=False, touchdown=False, first_down=False, penalty=False, pass_=None,
    )
    base.update(overrides)
    return base


def _two_game_raw() -> pl.DataFrame:
    # Two games sharing drive number 1 -- regression guard for the game_id+drive grouping bug.
    rows = [
        _row(game_id="G1", play_id=1.0, drive=1.0, down=1, ydstogo=10, yardline_100=75, posteam="AAA",
             defteam="BBB", play_type="run", pass_=False, rush=True),
        _row(game_id="G1", play_id=2.0, drive=1.0, down=2, ydstogo=7, yardline_100=72, posteam="AAA",
             defteam="BBB", play_type="pass", pass_=True, rush=False),
        _row(game_id="G2", play_id=1.0, drive=1.0, down=1, ydstogo=10, yardline_100=80, posteam="CCC",
             defteam="DDD", play_type="pass", pass_=True, rush=False),
    ]
    for r in rows:
        r["pass"] = r.pop("pass_")
    return pl.DataFrame(rows)


def test_prev_play_type_does_not_leak_across_games():
    raw = _two_game_raw()
    out = normalize_pbp(raw, season=2023)
    g2_play = out.filter((pl.col("game_id") == "G2") & (pl.col("play_id") == 1.0)).to_dicts()[0]
    # G2's first play must NOT see G1's run as its "previous play" just because both are drive=1
    assert g2_play["prev_play_type"] is None


def test_prev_play_type_within_same_drive():
    raw = _two_game_raw()
    out = normalize_pbp(raw, season=2023)
    g1_play2 = out.filter((pl.col("game_id") == "G1") & (pl.col("play_id") == 2.0)).to_dicts()[0]
    assert g1_play2["prev_play_type"] == "run"


def test_normalize_preserves_row_count_and_id_format():
    raw = _two_game_raw()
    out = normalize_pbp(raw, season=2023)
    assert out.height == 3
    assert set(out["id"].to_list()) == {"G1_1.0", "G1_2.0", "G2_1.0"}
    assert set(out["dataset_version"].to_list()) == {"nflverse:2023"}


def test_extract_games_dedupes_by_game_id():
    raw = _two_game_raw()
    games = extract_games(raw, season=2023)
    assert games.height == 2
    assert set(games["game_id"].to_list()) == {"G1", "G2"}
