from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import IngestionRun


def record_ingestion(
    db: Session,
    *,
    source: str,
    snapshot_id: str,
    dataset_version: str,
    mode: str,
    row_count: int,
    endpoint: str | None = None,
    notes: str | None = None,
) -> IngestionRun:
    run = IngestionRun(
        source=source,
        snapshot_id=snapshot_id,
        dataset_version=dataset_version,
        mode=mode,
        row_count=row_count,
        endpoint=endpoint,
        notes=notes,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
