from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Evidence
from app.schemas.discovery import EvidenceOut

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: str, db: Session = Depends(get_db)) -> Evidence:
    e = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not e:
        raise HTTPException(404, "evidence not found")
    return e
