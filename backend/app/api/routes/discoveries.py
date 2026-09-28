from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.discovery.engine import run_discovery
from app.models import Discovery, Evidence
from app.schemas.discovery import DiscoveryDetail, DiscoverySummary, EvidenceOut

router = APIRouter(prefix="/discoveries", tags=["discoveries"])


@router.get("", response_model=list[DiscoverySummary])
def list_discoveries(
    discovery_type: str | None = Query(None),
    team: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> list[Discovery]:
    q = db.query(Discovery)
    if discovery_type is not None:
        q = q.filter(Discovery.discovery_type == discovery_type)
    results = q.order_by(Discovery.adjusted_p_value.asc()).all()
    if team is not None:
        results = [d for d in results if team in (d.teams or [])]
    return results[:limit]


@router.get("/{discovery_id}", response_model=DiscoveryDetail)
def get_discovery(discovery_id: str, db: Session = Depends(get_db)) -> Discovery:
    d = db.query(Discovery).filter(Discovery.id == discovery_id).first()
    if not d:
        raise HTTPException(404, "discovery not found")
    return d


@router.get("/{discovery_id}/evidence", response_model=list[EvidenceOut])
def get_discovery_evidence(discovery_id: str, db: Session = Depends(get_db)) -> list[Evidence]:
    d = db.query(Discovery).filter(Discovery.id == discovery_id).first()
    if not d:
        raise HTTPException(404, "discovery not found")
    return db.query(Evidence).filter(Evidence.discovery_id == discovery_id).all()


@router.post("/run", response_model=list[DiscoverySummary])
def find_something_i_didnt_ask(db: Session = Depends(get_db)) -> list[Discovery]:
    """The killer feature (Section 45): re-runs the full discovery engine
    against the currently ingested data right now and returns whatever it
    found -- a real run, not a canned response."""
    return run_discovery(db)
