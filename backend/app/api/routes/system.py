from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.versioning import ALGORITHM_VERSIONS, FEATURE_VERSION, code_version
from app.db import get_db
from app.models import DiscoveredState, Discovery, Game, IngestionRun, Play, StateGraphNode, StateTransition
from app.schemas.misc import SystemStatus

router = APIRouter(tags=["system"])


@router.get("/system", response_model=SystemStatus)
def get_system_status(db: Session = Depends(get_db)) -> SystemStatus:
    last_run = db.query(IngestionRun).order_by(IngestionRun.retrieved_at.desc()).first()
    dataset_versions = sorted({r[0] for r in db.query(IngestionRun.dataset_version).distinct().all()})

    return SystemStatus(
        mode=settings.mode.value,
        code_version=code_version(),
        feature_version=FEATURE_VERSION,
        algorithm_versions=ALGORITHM_VERSIONS,
        dataset_versions=dataset_versions,
        last_ingestion=last_run.retrieved_at if last_run else None,
        n_games=db.query(func.count(Game.game_id)).scalar() or 0,
        n_plays=db.query(func.count(Play.id)).scalar() or 0,
        n_states=db.query(func.count(StateGraphNode.id)).scalar() or 0,
        n_discovered_states=db.query(func.count(DiscoveredState.id)).scalar() or 0,
        n_transitions=db.query(func.count(StateTransition.id)).scalar() or 0,
        n_discoveries=db.query(func.count(Discovery.id)).scalar() or 0,
        sportsdataio_configured=bool(settings.sportsdataio_api_key),
    )
