from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: str
    season: int
    week: int
    game_date: str | None
    home_team: str
    away_team: str
    dataset_version: str


class PlayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    game_id: str
    season: int
    week: int
    qtr: int | None
    down: float | None
    ydstogo: float | None
    yardline_100: float | None
    posteam: str | None
    defteam: str | None
    play_type: str | None
    epa: float | None
    desc: str | None


class TeamOut(BaseModel):
    team: str
    games: int
    plays: int


class PlayerOut(BaseModel):
    player_id: str
    name: str
    role: str  # passer | rusher | receiver
    plays: int


class SystemStatus(BaseModel):
    mode: str
    code_version: str
    feature_version: str
    algorithm_versions: dict[str, str]
    dataset_versions: list[str]
    last_ingestion: datetime | None
    n_games: int
    n_plays: int
    n_states: int
    n_discovered_states: int
    n_transitions: int
    n_discoveries: int
    sportsdataio_configured: bool
