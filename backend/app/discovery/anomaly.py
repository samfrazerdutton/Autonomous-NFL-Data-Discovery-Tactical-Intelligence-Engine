"""Anomaly detection (Section 11): team-weeks whose play-calling behavior
deviates from that team's own season baseline, beyond what a permutation test
says is plausible by chance.

Two complementary signals, both real and both required to flag a candidate:
  1. IsolationForest over standardized team-week behavior vectors (multivariate
     "does this team-week look unlike most team-weeks league-wide").
  2. A team-vs-own-baseline permutation test on pass rate (the specific,
     explainable deviation), which is what actually produces the Discovery's
     statistics (effect size, CI, p-value) -- IsolationForest is used only to
     rank/select candidates, never to manufacture a p-value.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.discovery.validation import passes_min_sample, two_sample_proportion_test

MIN_PLAYS_PER_TEAM_WEEK = 15


@dataclass
class AnomalyCandidate:
    team: str
    season: int
    week: int
    play_ids: list[str]
    baseline_play_ids: list[str]
    isolation_score: float
    stat: object
    seasons: list[int] = field(default_factory=list)


def _team_week_vectors(states: pl.DataFrame) -> pl.DataFrame:
    df = states.filter(pl.col("season_type") == "REG") if "season_type" in states.columns else states
    return (
        df.group_by(["posteam", "season", "week"])
        .agg(
            [
                pl.len().alias("n_plays"),
                pl.col("pass_play").cast(pl.Float64).mean().alias("pass_rate"),
                pl.col("epa").mean().alias("epa_mean"),
                (pl.col("yards_gained") >= 20).cast(pl.Float64).mean().alias("explosive_rate"),
            ]
        )
        .filter(pl.col("posteam").is_not_null() & (pl.col("n_plays") >= MIN_PLAYS_PER_TEAM_WEEK))
    )


def find_anomalous_team_weeks(states: pl.DataFrame, contamination: float = 0.05) -> list[AnomalyCandidate]:
    vectors = _team_week_vectors(states)
    if vectors.height < 20:
        return []

    feature_cols = ["pass_rate", "epa_mean", "explosive_rate"]
    X = vectors.select(feature_cols).fill_null(0).to_numpy()
    X_scaled = StandardScaler().fit_transform(X)

    iso = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    scores = iso.fit_predict(X_scaled)  # -1 = anomaly
    anomaly_scores = iso.score_samples(X_scaled)  # lower = more anomalous

    vectors = vectors.with_columns(
        [pl.Series("iso_flag", scores), pl.Series("iso_score", anomaly_scores)]
    )
    candidates_df = vectors.filter(pl.col("iso_flag") == -1)

    df_pass = states.select(["id", "posteam", "season", "week", "season_type", "pass_play"]).filter(
        (pl.col("season_type") == "REG") if "season_type" in states.columns else pl.lit(True)
    )

    results: list[AnomalyCandidate] = []
    for row in candidates_df.iter_rows(named=True):
        team, season, week = row["posteam"], row["season"], row["week"]
        week_plays = df_pass.filter(
            (pl.col("posteam") == team) & (pl.col("season") == season) & (pl.col("week") == week)
        )
        baseline_plays = df_pass.filter(
            (pl.col("posteam") == team) & ~((pl.col("season") == season) & (pl.col("week") == week))
        )
        if not passes_min_sample(week_plays.height, baseline_plays.height):
            continue
        sample_a = week_plays["pass_play"].fill_null(False).cast(pl.Int8).to_numpy()
        sample_b = baseline_plays["pass_play"].fill_null(False).cast(pl.Int8).to_numpy()
        stat = two_sample_proportion_test(sample_a, sample_b)
        results.append(
            AnomalyCandidate(
                team=team,
                season=season,
                week=week,
                play_ids=week_plays["id"].to_list(),
                baseline_play_ids=baseline_plays["id"].to_list()[:200],
                isolation_score=float(row["iso_score"]),
                stat=stat,
                seasons=sorted(states["season"].unique().to_list()),
            )
        )
    return results
