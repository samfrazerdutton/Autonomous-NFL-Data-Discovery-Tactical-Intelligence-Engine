from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Play
from app.schemas.misc import PlayOut

router = APIRouter(prefix="/plays", tags=["plays"])


@router.get("", response_model=list[PlayOut])
def list_plays(
    game_id: str | None = Query(None),
    team: str | None = Query(None),
    season: int | None = Query(None),
    week: int | None = Query(None),
    play_type: str | None = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
) -> list[Play]:
    q = db.query(Play)
    if game_id is not None:
        q = q.filter(Play.game_id == game_id)
    if team is not None:
        q = q.filter(Play.posteam == team)
    if season is not None:
        q = q.filter(Play.season == season)
    if week is not None:
        q = q.filter(Play.week == week)
    if play_type is not None:
        q = q.filter(Play.play_type == play_type)
    return q.order_by(Play.game_id, Play.play_id).limit(limit).all()
