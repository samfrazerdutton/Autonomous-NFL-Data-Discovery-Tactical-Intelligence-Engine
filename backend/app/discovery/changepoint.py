"""Change-point detection (Section 12): per-team regime shifts in pass rate
across the ordered sequence of weeks in the ingested seasons.

Uses ruptures' PELT algorithm (real, off-the-shelf changepoint detection, not
a hand-rolled threshold) to locate the single most significant break in each
team's weekly pass-rate series, then validates the shift with the same
permutation-test/bootstrap machinery as every other discovery type.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
import ruptures as rpt

from app.discovery.validation import passes_min_sample, two_sample_proportion_test

MIN_WEEKS = 8
MIN_WEEKS_PER_SEGMENT = 3


@dataclass
class ChangepointCandidate:
    team: str
    seasons: list[int]
    break_index: int  # index into the ordered week list
    before_weeks: list[tuple[int, int]]  # (season, week)
    after_weeks: list[tuple[int, int]]
    before_play_ids: list[str]
    after_play_ids: list[str]
    stat: object


def _team_weekly_series(states: pl.DataFrame, team: str) -> pl.DataFrame:
    df = states.filter(pl.col("posteam") == team)
    if "season_type" in df.columns:
        df = df.filter(pl.col("season_type") == "REG")
    weekly = (
        df.group_by(["season", "week"])
        .agg([pl.len().alias("n"), pl.col("pass_play").cast(pl.Float64).mean().alias("pass_rate")])
        .sort(["season", "week"])
    )
    return weekly


def find_changepoints(states: pl.DataFrame) -> list[ChangepointCandidate]:
    teams = sorted([t for t in states["posteam"].unique().to_list() if t])
    results: list[ChangepointCandidate] = []

    for team in teams:
        weekly = _team_weekly_series(states, team)
        if weekly.height < MIN_WEEKS:
            continue
        series = weekly["pass_rate"].to_numpy()
        algo = rpt.Pelt(model="rbf", min_size=MIN_WEEKS_PER_SEGMENT, jump=1).fit(series)
        try:
            breakpoints = algo.predict(pen=3.0)
        except Exception:
            continue
        breakpoints = [b for b in breakpoints if 0 < b < len(series)]
        if not breakpoints:
            continue

        # Largest mean-shift breakpoint is the one we report (Section 12: BEFORE -> CHANGE POINT -> AFTER)
        best_bp, best_shift = None, 0.0
        for bp in breakpoints:
            before_mean = series[:bp].mean()
            after_mean = series[bp:].mean()
            shift = abs(after_mean - before_mean)
            if shift > best_shift:
                best_shift, best_bp = shift, bp

        if best_bp is None:
            continue

        weeks = list(zip(weekly["season"].to_list(), weekly["week"].to_list()))
        before_weeks = weeks[:best_bp]
        after_weeks = weeks[best_bp:]
        if len(before_weeks) < MIN_WEEKS_PER_SEGMENT or len(after_weeks) < MIN_WEEKS_PER_SEGMENT:
            continue

        df = states.filter(pl.col("posteam") == team)
        if "season_type" in df.columns:
            df = df.filter(pl.col("season_type") == "REG")

        def _mask_for(weeks_list):
            m = pl.lit(False)
            for s, w in weeks_list:
                m = m | ((pl.col("season") == s) & (pl.col("week") == w))
            return m

        before_plays = df.filter(_mask_for(before_weeks))
        after_plays = df.filter(_mask_for(after_weeks))
        if not passes_min_sample(before_plays.height, after_plays.height):
            continue

        sample_before = before_plays["pass_play"].fill_null(False).cast(pl.Int8).to_numpy()
        sample_after = after_plays["pass_play"].fill_null(False).cast(pl.Int8).to_numpy()
        stat = two_sample_proportion_test(sample_after, sample_before)

        results.append(
            ChangepointCandidate(
                team=team,
                seasons=sorted(set(s for s, _ in weeks)),
                break_index=best_bp,
                before_weeks=before_weeks,
                after_weeks=after_weeks,
                before_play_ids=before_plays["id"].to_list()[:200],
                after_play_ids=after_plays["id"].to_list()[:200],
                stat=stat,
            )
        )
    return results
