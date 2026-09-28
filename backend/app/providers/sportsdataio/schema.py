"""Loose validation for SportsDataIO responses.

`extra="allow"` deliberately: this client has not been exercised against a
live subscription key, so these models capture the fields that are stable and
documented across SportsDataIO's NFL v3 API history without assuming the
full, exact shape of every field for every subscription tier.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SdioTeam(BaseModel):
    model_config = ConfigDict(extra="allow")

    Key: str
    FullName: str | None = None
    City: str | None = None
    Conference: str | None = None
    Division: str | None = None


class SdioScheduleGame(BaseModel):
    model_config = ConfigDict(extra="allow")

    GameKey: str
    Season: int
    Week: int
    AwayTeam: str
    HomeTeam: str
    Date: str | None = None
    AwayScore: int | None = None
    HomeScore: int | None = None
