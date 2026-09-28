"""Orchestrates: provider -> raw store -> normalization -> DB persistence.

This is Phase 1's ingestion pipeline. It currently drives the nflverse
provider only (LOCAL/DEMO); a SportsDataIO-backed pipeline would plug in here
identically once a key is configured, producing the same normalized Play rows.
"""
from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.versioning import dataset_version
from app.ingestion.raw_store import record_ingestion
from app.models import Game, IngestionRun, Play
from app.providers.nflverse import client as nflverse_client
from app.providers.nflverse.normalize import extract_games, normalize_pbp

logger = get_logger("ingestion.pipeline")


def ingest_season(db: Session, season: int, download: bool = False) -> IngestionRun:
    if download:
        nflverse_client.download_season(season)

    path, mode = nflverse_client.resolve_source(season)
    logger.info(f"ingesting season {season} from {path} (mode={mode})")

    import polars as pl

    raw = pl.read_parquet(path)
    games_df = extract_games(raw, season)
    plays_df = normalize_pbp(raw, season)
    dv = dataset_version("nflverse", str(season))

    db.execute(delete(Play).where(Play.season == season))
    db.execute(delete(Game).where(Game.season == season))
    db.commit()

    game_records = games_df.to_dicts()
    db.bulk_insert_mappings(Game, game_records)

    play_records = plays_df.to_dicts()
    db.bulk_insert_mappings(Play, play_records)
    db.commit()

    return record_ingestion(
        db,
        source="nflverse",
        snapshot_id=str(season),
        dataset_version=dv,
        mode=mode,
        row_count=len(play_records),
        endpoint=str(path.name),
        notes=f"{len(game_records)} games, {len(play_records)} plays",
    )


def ingest_seasons(db: Session, seasons: list[int], download: bool = False) -> list[IngestionRun]:
    return [ingest_season(db, s, download=download) for s in seasons]
