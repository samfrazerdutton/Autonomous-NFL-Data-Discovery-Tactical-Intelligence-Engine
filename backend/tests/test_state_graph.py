from __future__ import annotations

import polars as pl

from app.graph.state_graph import build_transitions, build_nodes


def _toy_states() -> pl.DataFrame:
    # One drive: 1st down run -> 2nd down pass -> touchdown (terminal, no next state)
    return pl.DataFrame(
        {
            "game_id": ["G1", "G1", "G1", "G2", "G2"],
            "drive": [1, 1, 1, 1, 1],
            "play_id": [1.0, 2.0, 3.0, 1.0, 2.0],
            "state_key": ["s1", "s2", "s3", "s1", "s2"],
            "down": [1, 2, 3, 1, 2],
            "distance_bucket": ["a"] * 5,
            "field_zone": ["a"] * 5,
            "score_bucket": ["a"] * 5,
            "qtr": [1] * 5,
            "play_type": ["run", "pass", "pass", "run", "run"],
            "pass_play": [False, True, True, False, False],
            "rush_play": [True, False, False, True, True],
            "epa": [0.1, 0.2, 1.0, -0.1, 0.3],
        }
    )


def test_transition_probabilities_sum_to_one_per_from_state_action():
    states = _toy_states()
    trans = build_transitions(states, "test:1")
    check = trans.group_by(["from_state_id", "action"]).agg(pl.col("probability").sum().alias("s"))
    assert (check["s"] - 1.0).abs().max() < 1e-9


def test_terminal_play_has_null_to_state():
    states = _toy_states()
    trans = build_transitions(states, "test:1")
    # s3 (drive-ending play, no next play in that drive) should transition to null
    terminal = trans.filter(pl.col("from_state_id") == "s3")
    assert terminal.height >= 1
    assert terminal["to_state_id"].null_count() == terminal.height


def test_build_nodes_aggregates_sample_size_and_rates():
    states = _toy_states()
    nodes = build_nodes(states, "test:1")
    s1 = nodes.filter(pl.col("id") == "s1").to_dicts()[0]
    assert s1["sample_size"] == 2
    assert s1["run_rate"] == 1.0
    assert s1["pass_rate"] == 0.0
