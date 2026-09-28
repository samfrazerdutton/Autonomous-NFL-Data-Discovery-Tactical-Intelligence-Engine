"""Minimal player identity derived from passer/rusher/receiver fields actually
present in nflverse pbp. No ratings, no fabricated attributes -- just
participation counts, honest about being a Phase 1-5 slice (full Player
Intelligence page per Section 24 is future work)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Play
from app.schemas.misc import PlayerOut

router = APIRouter(prefix="/players", tags=["players"])

ROLE_COLUMNS = [
    ("passer", Play.passer_player_id, Play.passer_player_name),
    ("rusher", Play.rusher_player_id, Play.rusher_player_name),
    ("receiver", Play.receiver_player_id, Play.receiver_player_name),
]


@router.get("", response_model=list[PlayerOut])
def list_players(role: str = Query("passer", pattern="^(passer|rusher|receiver)$"), limit: int = Query(50, le=200), db: Session = Depends(get_db)) -> list[PlayerOut]:
    id_col, name_col = next((idc, namec) for r, idc, namec in ROLE_COLUMNS if r == role)
    rows = (
        db.query(id_col, name_col, func.count(Play.id))
        .filter(id_col.is_not(None))
        .group_by(id_col, name_col)
        .order_by(func.count(Play.id).desc())
        .limit(limit)
        .all()
    )
    return [PlayerOut(player_id=pid, name=name or pid, role=role, plays=n) for pid, name, n in rows]
