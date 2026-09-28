"""Discovery Engine orchestrator (Section 7 / Phase 4).

Runs every discovery sub-module, pools ALL raw p-values produced across the
entire run for one shared Benjamini-Hochberg correction (Section 16 --
correcting each sub-module independently would understate the true multiple-
testing burden), and persists only the discoveries that survive correction
and the minimum-sample-size gate as fully evidenced Discovery rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl
from sqlalchemy.orm import Session

from app.core.versioning import ALGORITHM_VERSIONS, FEATURE_VERSION
from app.discovery import anomaly, changepoint, clustering, sequence
from app.discovery.validation import SIGNIFICANCE_ALPHA, benjamini_hochberg
from app.evidence.evidence_engine import build_evidence
from app.features.state_engine import build_football_states
from app.models import DiscoveredState, Discovery, Play

LIMITATIONS_COMMON = (
    "Associational, not causal: reflects historical co-occurrence within the ingested plays, "
    "not a controlled experiment. nflverse play-by-play does not include personnel-grouping data, "
    "so this analysis cannot account for player-level personnel effects."
)


@dataclass
class RawFinding:
    kind: str
    payload: Any
    p_value: float


def _play_frame(db: Session) -> pl.DataFrame:
    rows = [dict(r.__dict__) for r in db.query(Play).all()]
    for r in rows:
        r.pop("_sa_instance_state", None)
    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows)


def _dataset_version_label(states: pl.DataFrame) -> str:
    seasons = sorted(states["season"].unique().to_list())
    return "nflverse:" + "+".join(str(s) for s in seasons)


def _gather_findings(states: pl.DataFrame) -> list[RawFinding]:
    findings: list[RawFinding] = []

    _algo, _params, cluster_candidates = clustering.discover_clusters(states)
    for c in cluster_candidates:
        findings.append(RawFinding("cluster", c, c.stat.p_value))

    for a in anomaly.find_anomalous_team_weeks(states):
        findings.append(RawFinding("anomaly", a, a.stat.p_value))

    for cp in changepoint.find_changepoints(states):
        findings.append(RawFinding("changepoint", cp, cp.stat.p_value))

    for s in sequence.find_sequence_motifs(states):
        findings.append(RawFinding("sequence", s, s.stat.p_value))

    return findings


def _cluster_title(c) -> str:
    dom = c.feature_signature.get("dominant", {})
    down = (dom.get("down") or ["?"])[0]
    dist = (dom.get("distance_bucket") or ["?"])[0]
    zone = (dom.get("field_zone") or ["?"])[0]
    score = (dom.get("score_bucket") or ["?"])[0]
    direction = "above" if c.outcome["pass_rate"] > c.baseline["pass_rate"] else "below"
    return f"Down {down}, {dist.replace('_',' ')}, {zone.replace('_',' ')}, {score}: pass rate {direction} league baseline"


def _cluster_description(c) -> str:
    return (
        f"An unsupervised cluster ({c.algorithm} params={c.algorithm_params}) of {c.outcome['n']} plays sharing similar "
        f"pre-snap context (down/distance/field position/score/clock) shows a pass rate of {c.outcome['pass_rate']:.1%} "
        f"versus a {c.baseline['pass_rate']:.1%} league baseline across all scrimmage plays. Mean EPA in this cluster: "
        f"{c.outcome.get('epa_mean') and round(c.outcome['epa_mean'], 3)}."
    )


def _anomaly_title(a) -> str:
    direction = "higher" if a.stat.observed_a > a.stat.observed_b else "lower"
    return f"{a.team} pass rate {direction} than its own baseline in {a.season} Week {a.week}"


def _anomaly_description(a) -> str:
    return (
        f"{a.team}'s pass rate in {a.season} Week {a.week} was {a.stat.observed_a:.1%} across {a.stat.n_a} plays, "
        f"compared to a {a.stat.observed_b:.1%} baseline across the rest of that team's {a.stat.n_b} plays in the "
        f"ingested dataset. Flagged as multivariate-unusual by an IsolationForest over team-week behavior vectors "
        f"(isolation score {a.isolation_score:.3f}) before this specific pass-rate test was run."
    )


def _changepoint_title(cp) -> str:
    direction = "increased" if cp.stat.observed_a > cp.stat.observed_b else "decreased"
    after_season, after_week = cp.after_weeks[0]
    return f"{cp.team}'s pass rate {direction} starting around {after_season} Week {after_week}"


def _changepoint_description(cp) -> str:
    before_range = f"{cp.before_weeks[0][0]}wk{cp.before_weeks[0][1]}-{cp.before_weeks[-1][0]}wk{cp.before_weeks[-1][1]}"
    after_range = f"{cp.after_weeks[0][0]}wk{cp.after_weeks[0][1]}-{cp.after_weeks[-1][0]}wk{cp.after_weeks[-1][1]}"
    return (
        f"A PELT change-point detector found a break in {cp.team}'s weekly pass-rate series. "
        f"Before ({before_range}, n={cp.stat.n_b}): {cp.stat.observed_b:.1%} pass rate. "
        f"After ({after_range}, n={cp.stat.n_a}): {cp.stat.observed_a:.1%} pass rate."
    )


def _sequence_title(s) -> str:
    motif_str = " -> ".join(s.motif)
    return f"{s.team} runs '{motif_str}' at an unusual rate"


def _sequence_description(s) -> str:
    motif_str = " -> ".join(s.motif)
    return (
        f"Within drives, the sequence '{motif_str}' occurred in {s.stat.observed_a:.1%} of {s.team}'s "
        f"{s.team_windows}-window opportunities, versus {s.stat.observed_b:.1%} league-wide "
        f"(excluding {s.team}, n={s.stat.n_b} windows)."
    )


def run_discovery(db: Session) -> list[Discovery]:
    plays = _play_frame(db)
    if plays.height == 0:
        return []
    states = build_football_states(plays)
    dataset_version = _dataset_version_label(states)

    findings = _gather_findings(states)
    if not findings:
        return []

    p_values = [f.p_value for f in findings]
    adjusted = benjamini_hochberg(p_values, alpha=SIGNIFICANCE_ALPHA)

    discoveries: list[Discovery] = []
    for finding, adj_p in zip(findings, adjusted):
        if adj_p >= SIGNIFICANCE_ALPHA:
            continue

        kind = finding.kind
        payload = finding.payload
        stat = payload.stat

        common = dict(
            statistical_test="permutation test (two-sided) on proportion difference; bootstrap 95% CI",
            p_value=stat.p_value,
            adjusted_p_value=adj_p,
            confidence_interval=[stat.ci_low, stat.ci_high],
            effect_size=stat.effect_size,
            stability_score=stat.stability,
            replication_score=None,
            dataset_version=dataset_version,
            feature_version=FEATURE_VERSION,
        )

        if kind == "cluster":
            algorithm_version = ALGORITHM_VERSIONS["clustering"]
            discovered_state = DiscoveredState(
                algorithm=payload.algorithm,
                cluster_label=payload.cluster_label,
                feature_signature=payload.feature_signature,
                sample_size=payload.outcome["n"],
                teams=payload.teams,
                seasons=payload.seasons,
                outcome_distribution=payload.outcome,
                representative_play_ids=payload.play_ids[:10],
                novelty=payload.novelty,
                stability=payload.stability,
                algorithm_version=algorithm_version,
                dataset_version=dataset_version,
            )
            db.add(discovered_state)
            db.flush()

            d = Discovery(
                discovery_type="cluster",
                title=_cluster_title(payload),
                description=_cluster_description(payload),
                state_ids=[discovered_state.id],
                teams=payload.teams,
                seasons=payload.seasons,
                sample_size=payload.outcome["n"],
                baseline=payload.baseline,
                observed=payload.outcome,
                novelty_score=payload.novelty,
                limitations=LIMITATIONS_COMMON
                + " Cluster stability is a split-half agreement score for this run's clustering configuration as a "
                "whole, not a per-cluster figure.",
                algorithm_version=algorithm_version,
                evidence_ids=[],
                **common,
            )
        elif kind == "anomaly":
            algorithm_version = ALGORITHM_VERSIONS["anomaly"]
            d = Discovery(
                discovery_type="anomaly",
                title=_anomaly_title(payload),
                description=_anomaly_description(payload),
                teams=[payload.team],
                seasons=payload.seasons,
                sample_size=stat.n_a,
                baseline={"pass_rate": stat.observed_b, "n": stat.n_b},
                observed={"pass_rate": stat.observed_a, "n": stat.n_a, "isolation_score": payload.isolation_score},
                limitations=LIMITATIONS_COMMON
                + " A single flagged week may reflect game script (score state) rather than a deliberate scheme change.",
                algorithm_version=algorithm_version,
                evidence_ids=[],
                **common,
            )
        elif kind == "changepoint":
            algorithm_version = ALGORITHM_VERSIONS["changepoint"]
            d = Discovery(
                discovery_type="changepoint",
                title=_changepoint_title(payload),
                description=_changepoint_description(payload),
                teams=[payload.team],
                seasons=payload.seasons,
                sample_size=stat.n_a + stat.n_b,
                baseline={"pass_rate": stat.observed_b, "n": stat.n_b, "weeks": payload.before_weeks},
                observed={"pass_rate": stat.observed_a, "n": stat.n_a, "weeks": payload.after_weeks},
                limitations=LIMITATIONS_COMMON
                + " A single detected breakpoint per team per run; does not rule out gradual drift or multiple "
                "regime changes within the window.",
                algorithm_version=algorithm_version,
                evidence_ids=[],
                **common,
            )
        elif kind == "sequence":
            algorithm_version = ALGORITHM_VERSIONS["sequence"]
            d = Discovery(
                discovery_type="sequence",
                title=_sequence_title(payload),
                description=_sequence_description(payload),
                sequence_pattern=list(payload.motif),
                teams=[payload.team],
                seasons=sorted(states["season"].unique().to_list()),
                sample_size=stat.n_a,
                baseline={"rate": stat.observed_b, "n": stat.n_b},
                observed={"rate": stat.observed_a, "n": stat.n_a},
                limitations=LIMITATIONS_COMMON
                + " Motif rate is measured over sliding windows within drives, so overlapping windows from the same "
                "drive are not fully independent observations.",
                algorithm_version=algorithm_version,
                evidence_ids=[],
                **common,
            )
        else:
            continue

        db.add(d)
        db.flush()

        if kind == "cluster":
            evidence_ids = build_evidence(
                db, discovery_id=d.id, play_ids=payload.play_ids, source="nflverse", dataset_version=dataset_version
            )
        elif kind == "anomaly":
            evidence_ids = build_evidence(
                db, discovery_id=d.id, play_ids=payload.play_ids, source="nflverse", dataset_version=dataset_version
            )
        elif kind == "changepoint":
            evidence_ids = build_evidence(
                db,
                discovery_id=d.id,
                play_ids=payload.after_play_ids,
                source="nflverse",
                dataset_version=dataset_version,
                description_fn=lambda p: f"[AFTER change point] {p.desc or p.id}",
            )
            evidence_ids += build_evidence(
                db,
                discovery_id=d.id,
                play_ids=payload.before_play_ids[:10],
                source="nflverse",
                dataset_version=dataset_version,
                role="counterexample",
                description_fn=lambda p: f"[BEFORE change point] {p.desc or p.id}",
                limit=10,
            )
        elif kind == "sequence":
            flat_ids = [pid for group in payload.example_play_id_groups for pid in group]
            evidence_ids = build_evidence(
                db, discovery_id=d.id, play_ids=flat_ids, source="nflverse", dataset_version=dataset_version, limit=25
            )
        else:
            evidence_ids = []

        d.evidence_ids = evidence_ids
        db.add(d)
        discoveries.append(d)

    db.commit()
    return discoveries
