"""SQLAlchemy ORM models.

JSON-ish columns (lists/dicts) use SQLAlchemy's JSON type, which SQLite backs
with TEXT + Python-side (de)serialization -- no extension required.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String)  # "nflverse" | "sportsdataio" | "sample"
    snapshot_id: Mapped[str] = mapped_column(String)  # e.g. season "2023"
    dataset_version: Mapped[str] = mapped_column(String, index=True)
    mode: Mapped[str] = mapped_column(String)  # LIVE | LOCAL | DEMO
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    endpoint: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Game(Base):
    __tablename__ = "games"

    game_id: Mapped[str] = mapped_column(String, primary_key=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int] = mapped_column(Integer, index=True)
    game_date: Mapped[str | None] = mapped_column(String, nullable=True)
    home_team: Mapped[str] = mapped_column(String, index=True)
    away_team: Mapped[str] = mapped_column(String, index=True)
    dataset_version: Mapped[str] = mapped_column(String)

    plays: Mapped[list["Play"]] = relationship(back_populates="game")


class Play(Base):
    __tablename__ = "plays"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # f"{game_id}_{play_id}"
    game_id: Mapped[str] = mapped_column(ForeignKey("games.game_id"), index=True)
    play_id: Mapped[float] = mapped_column(Float)
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int] = mapped_column(Integer, index=True)
    season_type: Mapped[str | None] = mapped_column(String, index=True, nullable=True)  # REG | POST

    # Game state
    qtr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_seconds_remaining: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_differential: Mapped[float | None] = mapped_column(Float, nullable=True)
    posteam: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    defteam: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    posteam_type: Mapped[str | None] = mapped_column(String, nullable=True)  # home | away

    # Field state
    down: Mapped[float | None] = mapped_column(Float, nullable=True)
    ydstogo: Mapped[float | None] = mapped_column(Float, nullable=True)
    yardline_100: Mapped[float | None] = mapped_column(Float, nullable=True)
    goal_to_go: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Temporal / drive state
    drive: Mapped[float | None] = mapped_column(Float, nullable=True)
    play_num_in_drive: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prev_play_type: Mapped[str | None] = mapped_column(String, nullable=True)
    prev_play_type_2: Mapped[str | None] = mapped_column(String, nullable=True)

    # Tactical state / outcome
    play_type: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    pass_play: Mapped[bool | None] = mapped_column(nullable=True)
    rush_play: Mapped[bool | None] = mapped_column(nullable=True)
    shotgun: Mapped[bool | None] = mapped_column(nullable=True)
    no_huddle: Mapped[bool | None] = mapped_column(nullable=True)
    complete_pass: Mapped[bool | None] = mapped_column(nullable=True)
    incomplete_pass: Mapped[bool | None] = mapped_column(nullable=True)
    interception: Mapped[bool | None] = mapped_column(nullable=True)
    fumble_lost: Mapped[bool | None] = mapped_column(nullable=True)
    touchdown: Mapped[bool | None] = mapped_column(nullable=True)
    first_down: Mapped[bool | None] = mapped_column(nullable=True)
    penalty: Mapped[bool | None] = mapped_column(nullable=True)
    epa: Mapped[float | None] = mapped_column(Float, nullable=True)
    air_yards: Mapped[float | None] = mapped_column(Float, nullable=True)
    yards_gained: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Personnel (only populated where the source actually provides it)
    offense_personnel: Mapped[str | None] = mapped_column(String, nullable=True)
    defense_personnel: Mapped[str | None] = mapped_column(String, nullable=True)
    passer_player_id: Mapped[str | None] = mapped_column(String, nullable=True)
    passer_player_name: Mapped[str | None] = mapped_column(String, nullable=True)
    rusher_player_id: Mapped[str | None] = mapped_column(String, nullable=True)
    rusher_player_name: Mapped[str | None] = mapped_column(String, nullable=True)
    receiver_player_id: Mapped[str | None] = mapped_column(String, nullable=True)
    receiver_player_name: Mapped[str | None] = mapped_column(String, nullable=True)

    desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    dataset_version: Mapped[str] = mapped_column(String, index=True)

    game: Mapped["Game"] = relationship(back_populates="plays")


class StateGraphNode(Base):
    """Deterministic, interpretable state-graph node (Section 9)."""

    __tablename__ = "state_graph_nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # deterministic state_key
    down: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_bucket: Mapped[str] = mapped_column(String)
    field_zone: Mapped[str] = mapped_column(String)
    score_bucket: Mapped[str] = mapped_column(String)
    qtr: Mapped[int] = mapped_column(Integer)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    run_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    epa_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    action_entropy: Mapped[float | None] = mapped_column(Float, nullable=True)
    dataset_version: Mapped[str] = mapped_column(String, index=True)


class StateTransition(Base):
    __tablename__ = "state_transitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    from_state_id: Mapped[str] = mapped_column(ForeignKey("state_graph_nodes.id"), index=True)
    to_state_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # null = drive-ending
    action: Mapped[str] = mapped_column(String)  # pass | run | punt | field_goal | turnover | ...
    count: Mapped[int] = mapped_column(Integer, default=0)
    probability: Mapped[float] = mapped_column(Float, default=0.0)
    dataset_version: Mapped[str] = mapped_column(String, index=True)


class DiscoveredState(Base):
    """Unsupervised cluster over the continuous feature vector (Section 8)."""

    __tablename__ = "discovered_states"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    algorithm: Mapped[str] = mapped_column(String)
    cluster_label: Mapped[int] = mapped_column(Integer)
    feature_signature: Mapped[dict] = mapped_column(JSON)  # centroid / medoid feature values
    sample_size: Mapped[int] = mapped_column(Integer)
    teams: Mapped[list] = mapped_column(JSON)
    seasons: Mapped[list] = mapped_column(JSON)
    outcome_distribution: Mapped[dict] = mapped_column(JSON)
    representative_play_ids: Mapped[list] = mapped_column(JSON)
    novelty: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    silhouette: Mapped[float | None] = mapped_column(Float, nullable=True)
    dataset_version: Mapped[str] = mapped_column(String, index=True)
    algorithm_version: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Discovery(Base):
    __tablename__ = "discoveries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    discovery_type: Mapped[str] = mapped_column(String, index=True)  # cluster|anomaly|changepoint|sequence
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)

    state_ids: Mapped[list] = mapped_column(JSON, default=list)
    sequence_pattern: Mapped[list | None] = mapped_column(JSON, nullable=True)
    teams: Mapped[list] = mapped_column(JSON, default=list)
    players: Mapped[list] = mapped_column(JSON, default=list)
    seasons: Mapped[list] = mapped_column(JSON, default=list)

    sample_size: Mapped[int] = mapped_column(Integer)
    baseline: Mapped[dict] = mapped_column(JSON)
    observed: Mapped[dict] = mapped_column(JSON)
    effect_size: Mapped[float] = mapped_column(Float)
    novelty_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    replication_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    statistical_test: Mapped[str] = mapped_column(String)
    p_value: Mapped[float] = mapped_column(Float)
    adjusted_p_value: Mapped[float] = mapped_column(Float)
    confidence_interval: Mapped[list] = mapped_column(JSON)  # [lo, hi]

    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    counterexample_ids: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[str] = mapped_column(Text)

    dataset_version: Mapped[str] = mapped_column(String, index=True)
    algorithm_version: Mapped[str] = mapped_column(String)
    feature_version: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    discovery_id: Mapped[str | None] = mapped_column(ForeignKey("discoveries.id"), nullable=True, index=True)
    game_id: Mapped[str | None] = mapped_column(String, nullable=True)
    play_id: Mapped[str | None] = mapped_column(String, nullable=True)  # Play.id
    role: Mapped[str] = mapped_column(String, default="supporting")  # supporting | counterexample
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String)  # nflverse | sportsdataio | sample
    endpoint: Mapped[str | None] = mapped_column(String, nullable=True)
    retrieval_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dataset_version: Mapped[str] = mapped_column(String)
