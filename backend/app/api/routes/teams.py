from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game, Play
from app.schemas.misc import TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)) -> list[TeamOut]:
    teams = sorted({t for (t,) in db.query(Game.home_team).distinct().all()})
    out = []
    for t in teams:
        n_games = (
            db.query(func.count(Game.game_id)).filter((Game.home_team == t) | (Game.away_team == t)).scalar() or 0
        )
        n_plays = db.query(func.count(Play.id)).filter(Play.posteam == t).scalar() or 0
        out.append(TeamOut(team=t, games=n_games, plays=n_plays))
    return out
