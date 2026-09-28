from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StateNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    down: int | None
    distance_bucket: str
    field_zone: str
    score_bucket: str
    qtr: int
    sample_size: int
    pass_rate: float | None
    run_rate: float | None
    epa_mean: float | None
    action_entropy: float | None
    dataset_version: str


class TransitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_state_id: str
    action: str
    to_state_id: str | None
    count: int
    probability: float


class DiscoveredStateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    algorithm: str
    cluster_label: int
    feature_signature: dict
    sample_size: int
    teams: list[str]
    seasons: list[int]
    outcome_distribution: dict
    representative_play_ids: list[str]
    novelty: float | None
    stability: float | None
    algorithm_version: str
    dataset_version: str
