from __future__ import annotations

import numpy as np
import polars as pl

from app.discovery.clustering import discover_clusters
from app.features.state_engine import STATE_FEATURE_COLUMNS, distance_bucket, field_zone, score_bucket


def _synthetic_states(n_per_group: int = 150) -> pl.DataFrame:
    """Two well-separated synthetic state groups with clearly different pass rates,
    so a real clustering pass should recover the separation and flag a significant
    outcome difference for at least one cluster."""
    rng = np.random.default_rng(0)
    rows = []
    for group, pass_rate in [(0, 0.85), (1, 0.15)]:
        for i in range(n_per_group):
            rows.append(
                {
                    "id": f"g{group}_{i}",
                    "posteam": "AAA" if i % 2 == 0 else "BBB",
                    "season": 2023,
                    "down": 1 if group == 0 else 3,
                    "ydstogo": (10.0 if group == 0 else 2.0),
                    "yardline_100": (70.0 if group == 0 else 20.0),
                    "distance_bucket": distance_bucket(10.0 if group == 0 else 2.0),
                    "field_zone": field_zone(70.0 if group == 0 else 20.0),
                    "score_bucket": score_bucket(0.0),
                    "score_differential": 0.0,
                    "qtr": 1,
                    "game_seconds_remaining": 1800.0,
                    "play_num_in_drive": 1,
                    "prev_is_pass": 0,
                    "prev_is_run": 0,
                    "prev2_is_pass": 0,
                    "prev2_is_run": 0,
                    "pass_play": bool(rng.random() < pass_rate),
                    "rush_play": None,
                    "epa": float(rng.normal(0, 1)),
                    "first_down": bool(rng.random() < 0.3),
                    "touchdown": bool(rng.random() < 0.05),
                    "interception": False,
                    "fumble_lost": False,
                }
            )
    df = pl.DataFrame(rows)
    return df.with_columns((~pl.col("pass_play")).alias("rush_play"))


def test_discover_clusters_runs_and_returns_valid_candidates():
    states = _synthetic_states()
    algorithm, params, candidates = discover_clusters(states)

    assert algorithm in {"kmeans", "gmm", "hdbscan"}
    assert isinstance(candidates, list)
    for c in candidates:
        assert c.outcome["n"] >= 30
        assert 0.0 <= c.novelty <= 1.0
        assert 0.0 <= c.stability <= 1.0
        assert set(c.feature_signature.keys()) >= set(STATE_FEATURE_COLUMNS)
        assert -1.0 <= c.stat.p_value <= 1.0


def test_discover_clusters_separates_the_two_synthetic_groups():
    states = _synthetic_states()
    _algorithm, _params, candidates = discover_clusters(states)
    # At least one cluster should show a pass rate well above the ~50% blended baseline
    # and at least one well below it -- i.e. clustering actually found the synthetic split.
    pass_rates = [c.outcome["pass_rate"] for c in candidates]
    assert any(p > 0.7 for p in pass_rates)
    assert any(p < 0.3 for p in pass_rates)
