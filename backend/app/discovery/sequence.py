"""Sequence motif mining (Section 10): recurring play-type n-grams within
drives that occur at a team-specific rate significantly different from the
rest of the league, not predefined by hand.

Approach: enumerate every observed 2- and 3-gram of pass/run calls within each
drive (in play order), tabulate occurrence rates per team vs. league-minus-team,
screen for motifs+teams where the descriptive deviation is large enough to be
worth a real hypothesis test (bounds the multiple-testing burden), then run
the same permutation-test/bootstrap machinery as every other discovery type on
the screened candidates. Only pass/run tokens are used -- special-teams plays
end a drive's offensive sequence rather than appearing as a token, since a motif
about play-calling shouldn't be diluted by punts/field goals.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from app.discovery.validation import passes_min_sample, two_sample_proportion_test

NGRAM_SIZES = (2, 3)
MIN_LEAGUE_OCCURRENCES = 50
MIN_TEAM_WINDOWS = 30
SCREEN_RATIO = 1.4  # descriptive pre-filter before running the expensive test
MAX_CANDIDATES_TESTED = 60


@dataclass
class SequenceCandidate:
    team: str
    motif: tuple[str, ...]
    team_windows: int
    league_windows: int
    example_play_id_groups: list[list[str]]
    stat: object


def _drive_tokens(states: pl.DataFrame) -> pl.DataFrame:
    df = states.filter(pl.col("play_type").is_in(["pass", "run"]) & pl.col("posteam").is_not_null())
    df = df.sort(["game_id", "drive", "play_id"])
    return df.select(["game_id", "drive", "posteam", "play_id", "play_type"])


def _windows(tokens: pl.DataFrame, n: int) -> list[dict]:
    out = []
    for (game_id, drive, team), group in tokens.group_by(["game_id", "drive", "posteam"]):
        seq = group.sort("play_id")
        types = seq["play_type"].to_list()
        ids = seq["play_id"].to_list()
        pids = [f"{game_id}_{pid}" for pid in ids]
        for i in range(len(types) - n + 1):
            out.append(
                {
                    "team": team,
                    "motif": tuple(types[i : i + n]),
                    "play_ids": pids[i : i + n],
                }
            )
    return out


def find_sequence_motifs(states: pl.DataFrame) -> list[SequenceCandidate]:
    tokens = _drive_tokens(states)
    if tokens.height == 0:
        return []

    results: list[SequenceCandidate] = []
    tested = 0

    for n in NGRAM_SIZES:
        windows = _windows(tokens, n)
        if not windows:
            continue

        motif_team_count: dict[tuple, dict[str, int]] = {}
        motif_examples: dict[tuple, dict[str, list[list[str]]]] = {}
        team_total_windows: dict[str, int] = {}

        for w in windows:
            motif_team_count.setdefault(w["motif"], {}).setdefault(w["team"], 0)
            motif_team_count[w["motif"]][w["team"]] += 1
            team_total_windows[w["team"]] = team_total_windows.get(w["team"], 0) + 1
            exs = motif_examples.setdefault(w["motif"], {}).setdefault(w["team"], [])
            if len(exs) < 5:
                exs.append(w["play_ids"])

        for motif, team_counts in motif_team_count.items():
            league_total = sum(team_counts.values())
            if league_total < MIN_LEAGUE_OCCURRENCES:
                continue
            all_windows_total = sum(team_total_windows.values())
            league_rate = league_total / all_windows_total

            for team, count in team_counts.items():
                team_windows_total = team_total_windows[team]
                if team_windows_total < MIN_TEAM_WINDOWS:
                    continue
                team_rate = count / team_windows_total
                if league_rate == 0:
                    continue
                ratio = team_rate / league_rate
                if ratio < SCREEN_RATIO and ratio > 1 / SCREEN_RATIO:
                    continue  # not descriptively unusual enough to warrant a formal test
                if tested >= MAX_CANDIDATES_TESTED:
                    continue

                rest_total = league_total - count
                rest_windows = team_windows_total_rest = sum(
                    v for t, v in team_total_windows.items() if t != team
                )
                if rest_windows == 0 or not passes_min_sample(team_windows_total, rest_windows):
                    continue

                sample_a = np.zeros(team_windows_total, dtype=np.int8)
                sample_a[:count] = 1
                sample_b = np.zeros(rest_windows, dtype=np.int8)
                sample_b[:rest_total] = 1

                tested += 1
                stat = two_sample_proportion_test(sample_a, sample_b, n_perm=2000, max_side_n=3000)
                results.append(
                    SequenceCandidate(
                        team=team,
                        motif=motif,
                        team_windows=team_windows_total,
                        league_windows=rest_windows,
                        example_play_id_groups=motif_examples[motif].get(team, []),
                        stat=stat,
                    )
                )
    return results
