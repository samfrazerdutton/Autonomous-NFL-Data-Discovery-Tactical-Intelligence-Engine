from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DiscoveredState, StateGraphNode, StateTransition
from app.schemas.state import DiscoveredStateOut, StateNodeOut, TransitionOut

router = APIRouter(prefix="/states", tags=["states"])


@router.get("", response_model=list[StateNodeOut])
def list_states(
    down: int | None = Query(None),
    min_sample_size: int = Query(1),
    limit: int = Query(200, le=2000),
    db: Session = Depends(get_db),
) -> list[StateGraphNode]:
    q = db.query(StateGraphNode).filter(StateGraphNode.sample_size >= min_sample_size)
    if down is not None:
        q = q.filter(StateGraphNode.down == down)
    return q.order_by(StateGraphNode.sample_size.desc()).limit(limit).all()


@router.get("/discovered", response_model=list[DiscoveredStateOut])
def list_discovered_states(db: Session = Depends(get_db)) -> list[DiscoveredState]:
    return db.query(DiscoveredState).order_by(DiscoveredState.sample_size.desc()).all()


@router.get("/discovered/{state_id}", response_model=DiscoveredStateOut)
def get_discovered_state(state_id: str, db: Session = Depends(get_db)) -> DiscoveredState:
    s = db.query(DiscoveredState).filter(DiscoveredState.id == state_id).first()
    if not s:
        raise HTTPException(404, "discovered state not found")
    return s


@router.get("/{state_id}", response_model=StateNodeOut)
def get_state(state_id: str, db: Session = Depends(get_db)) -> StateGraphNode:
    s = db.query(StateGraphNode).filter(StateGraphNode.id == state_id).first()
    if not s:
        raise HTTPException(404, "state not found")
    return s


@router.get("/{state_id}/transitions", response_model=list[TransitionOut])
def get_transitions(state_id: str, db: Session = Depends(get_db)) -> list[StateTransition]:
    return (
        db.query(StateTransition)
        .filter(StateTransition.from_state_id == state_id)
        .order_by(StateTransition.probability.desc())
        .all()
    )
