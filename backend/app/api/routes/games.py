from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game
from app.schemas.misc import GameOut

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=list[GameOut])
def list_games(
    season: int | None = Query(None),
    week: int | None = Query(None),
    team: str | None = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
) -> list[Game]:
    q = db.query(Game)
    if season is not None:
        q = q.filter(Game.season == season)
    if week is not None:
        q = q.filter(Game.week == week)
    if team is not None:
        q = q.filter((Game.home_team == team) | (Game.away_team == team))
    return q.order_by(Game.season, Game.week).limit(limit).all()


@router.get("/{game_id}", response_model=GameOut)
def get_game(game_id: str, db: Session = Depends(get_db)) -> Game:
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        from fastapi import HTTPException

        raise HTTPException(404, "game not found")
    return game
