from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.ingestion.pipeline import ingest_seasons

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    seasons: list[int]
    download: bool = False


class IngestResponse(BaseModel):
    season: str
    mode: str
    dataset_version: str
    row_count: int


@router.post("", response_model=list[IngestResponse])
def ingest(req: IngestRequest, db: Session = Depends(get_db)) -> list[IngestResponse]:
    runs = ingest_seasons(db, req.seasons, download=req.download)
    return [
        IngestResponse(season=r.snapshot_id, mode=r.mode, dataset_version=r.dataset_version, row_count=r.row_count)
        for r in runs
    ]
