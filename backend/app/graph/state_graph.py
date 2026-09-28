"""State Graph (Section 9 / Phase 3).

Represents the game as STATE_t -> ACTION -> STATE_t+1, using the deterministic
state-key defined in features.state_engine (down/distance-bucket/field-zone/
score-bucket/quarter). Computes real transition frequencies, conditional
probabilities P(next_state | state, action), per-state action entropy, and
graph centrality over the resulting directed multigraph -- no invented
numbers, everything aggregated from the ingested plays.
"""
from __future__ import annotations

import math

import networkx as nx
import polars as pl
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import StateGraphNode, StateTransition

ACTIONS = {"pass", "run", "punt", "field_goal", "qb_kneel", "qb_spike"}


def _action(play_type: str | None) -> str:
    return play_type if play_type in ACTIONS else "other"


def build_nodes(states: pl.DataFrame, dataset_version: str) -> pl.DataFrame:
    agg = states.group_by(["state_key", "down", "distance_bucket", "field_zone", "score_bucket", "qtr"]).agg(
        [
            pl.len().alias("sample_size"),
            pl.col("pass_play").cast(pl.Float64).mean().alias("pass_rate"),
            pl.col("rush_play").cast(pl.Float64).mean().alias("run_rate"),
            pl.col("epa").mean().alias("epa_mean"),
        ]
    )
    return agg.with_columns(
        [pl.col("state_key").alias("id"), pl.lit(dataset_version).alias("dataset_version")]
    )


def build_transitions(states: pl.DataFrame, dataset_version: str) -> pl.DataFrame:
    df = states.sort(["game_id", "drive", "play_id"]).with_columns(
        [
            pl.col("play_type").map_elements(_action, return_dtype=pl.Utf8).alias("action"),
            pl.col("state_key").shift(-1).over(["game_id", "drive"]).alias("to_state_id"),
        ]
    )
    counts = df.group_by(["state_key", "action", "to_state_id"]).agg(pl.len().alias("count"))
    counts = counts.rename({"state_key": "from_state_id"})
    totals = counts.group_by(["from_state_id", "action"]).agg(pl.col("count").sum().alias("total"))
    counts = counts.join(totals, on=["from_state_id", "action"])
    counts = counts.with_columns((pl.col("count") / pl.col("total")).alias("probability"))
    counts = counts.with_columns(pl.lit(dataset_version).alias("dataset_version"))
    return counts.select(["from_state_id", "action", "to_state_id", "count", "probability", "dataset_version"])


def action_entropy_by_state(states: pl.DataFrame) -> dict[str, float]:
    """Shannon entropy (bits) of P(action | state) -- how predictable the play call is."""
    df = states.with_columns(pl.col("play_type").map_elements(_action, return_dtype=pl.Utf8).alias("action"))
    counts = df.group_by(["state_key", "action"]).agg(pl.len().alias("n"))
    totals = counts.group_by("state_key").agg(pl.col("n").sum().alias("total"))
    counts = counts.join(totals, on="state_key").with_columns((pl.col("n") / pl.col("total")).alias("p"))

    entropy: dict[str, float] = {}
    for row in counts.iter_rows(named=True):
        h = entropy.get(row["state_key"], 0.0)
        p = row["p"]
        if p > 0:
            h -= p * math.log2(p)
        entropy[row["state_key"]] = h
    return entropy


def build_networkx_graph(transitions: pl.DataFrame) -> nx.DiGraph:
    g = nx.DiGraph()
    agg = transitions.filter(pl.col("to_state_id").is_not_null()).group_by(["from_state_id", "to_state_id"]).agg(
        pl.col("count").sum().alias("weight")
    )
    for row in agg.iter_rows(named=True):
        g.add_edge(row["from_state_id"], row["to_state_id"], weight=row["weight"])
    return g


def persist_graph(db: Session, states: pl.DataFrame, dataset_version: str) -> tuple[int, int]:
    nodes = build_nodes(states, dataset_version)
    transitions = build_transitions(states, dataset_version)
    entropy = action_entropy_by_state(states)

    db.execute(delete(StateTransition))
    db.execute(delete(StateGraphNode))
    db.commit()

    node_records = nodes.to_dicts()
    for r in node_records:
        r.pop("state_key", None)
        r["action_entropy"] = entropy.get(r["id"])
    db.bulk_insert_mappings(StateGraphNode, node_records)

    trans_records = transitions.to_dicts()
    db.bulk_insert_mappings(StateTransition, trans_records)
    db.commit()
    return len(node_records), len(trans_records)


def centrality_metrics(g: nx.DiGraph) -> dict[str, dict[str, float]]:
    if g.number_of_nodes() == 0:
        return {}
    pagerank = nx.pagerank(g, weight="weight")
    betweenness = nx.betweenness_centrality(g, weight="weight", normalized=True)
    return {
        node: {"pagerank": pagerank.get(node, 0.0), "betweenness": betweenness.get(node, 0.0)}
        for node in g.nodes
    }
