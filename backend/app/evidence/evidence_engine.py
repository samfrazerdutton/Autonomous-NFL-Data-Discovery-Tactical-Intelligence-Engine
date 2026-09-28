"""Evidence Engine (Section 19): traces a Discovery to the exact plays that
produced it.

A cluster or team-week candidate can involve thousands of plays; storing one
Evidence row per play would bloat the database for no analytical benefit, so
this stores a representative, explicitly-labeled sample (capped by `limit`)
alongside the Discovery's own `sample_size` field, which always records the
true full count the statistics were computed over.
"""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.models import Evidence, Play

DEFAULT_LIMIT = 15


def build_evidence(
    db: Session,
    *,
    discovery_id: str | None,
    play_ids: list[str],
    source: str,
    dataset_version: str,
    role: str = "supporting",
    limit: int = DEFAULT_LIMIT,
    description_fn: Callable[[Play], str] | None = None,
) -> list[str]:
    if not play_ids:
        return []
    selected = play_ids[:limit]
    plays = db.query(Play).filter(Play.id.in_(selected)).all()
    plays_by_id = {p.id: p for p in plays}

    evidences = []
    for pid in selected:
        p = plays_by_id.get(pid)
        if p is None:
            continue
        description = description_fn(p) if description_fn else (p.desc or f"{p.game_id} play {p.play_id}")
        ev = Evidence(
            discovery_id=discovery_id,
            game_id=p.game_id,
            play_id=p.id,
            role=role,
            description=description,
            source=source,
            dataset_version=dataset_version,
        )
        db.add(ev)
        evidences.append(ev)
    db.flush()
    return [e.id for e in evidences]
