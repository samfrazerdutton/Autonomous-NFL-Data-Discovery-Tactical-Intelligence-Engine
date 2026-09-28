from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DiscoverySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    discovery_type: str
    title: str
    description: str
    teams: list[str]
    seasons: list[int]
    sample_size: int
    effect_size: float
    p_value: float
    adjusted_p_value: float
    confidence_interval: list[float]
    stability_score: float | None
    novelty_score: float | None
    dataset_version: str
    algorithm_version: str
    created_at: datetime


class DiscoveryDetail(DiscoverySummary):
    state_ids: list[str]
    sequence_pattern: list[str] | None
    players: list[str]
    baseline: dict
    observed: dict
    statistical_test: str
    replication_score: float | None
    evidence_ids: list[str]
    counterexample_ids: list[str]
    limitations: str
    feature_version: str


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    discovery_id: str | None
    game_id: str | None
    play_id: str | None
    role: str
    description: str
    source: str
    dataset_version: str
